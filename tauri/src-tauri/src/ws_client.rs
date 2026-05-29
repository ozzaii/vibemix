//! Phase 11 Wave 2 + Wave 4 — WS bus client.
//!
//! Connects to `ws://127.0.0.1:8765` (the Python sidecar's
//! `vibemix.runtime.ws_bus` from Phase 4 / wizard bus from Wave 4) and
//! forwards every inbound `Message::Text` payload to the webview as
//! `ipc:<type>` via `tauri::Emitter`. Webview never opens its own
//! socket — RESEARCH anti-pattern §"Webview hardcoded localhost".
//!
//! Reconnects with exponential backoff 250 ms → 5000 ms cap.
//!
//! Wave 4 adds the outbound half: `forward_ipc_to_sidecar` is a
//! `#[tauri::command]` the webview invokes to send an ipc.* envelope
//! to the sidecar. The active WebSocket `SplitSink` is parked behind
//! a `WsClientHandle` (managed Tauri state); the command grabs the
//! lock, serializes the JSON, and sends it. Disconnected → returns
//! a structured error which the TS client surfaces.
//!
//! Validation rule (per plan): we do NOT validate the schema here —
//! Python validates on serialize, webview validates on receive via ajv
//! (Wave 0). Double validation in Rust adds latency without value.

use std::sync::Arc;
use std::time::Duration;

use futures_util::stream::SplitSink;
use futures_util::{SinkExt, StreamExt};
use tauri::{AppHandle, Emitter, Manager};
use tokio::net::TcpStream;
use tokio::sync::Mutex;
use tokio_tungstenite::{connect_async, tungstenite::Message, MaybeTlsStream, WebSocketStream};

const WS_URL: &str = "ws://127.0.0.1:8765";
const BACKOFF_START_MS: u64 = 250;
const BACKOFF_CAP_MS: u64 = 5000;
// After this many consecutive connect failures (~30s of reconnect
// attempts with the 250→5000ms backoff), emit ws-state=unreachable so
// the webview can show an actionable banner instead of perpetual
// "reconnecting…". Reset to 0 on a successful connect.
const UNREACHABLE_AFTER: u32 = 12;

type WsSink = SplitSink<WebSocketStream<MaybeTlsStream<TcpStream>>, Message>;

/// Managed state holding the outbound `SplitSink` of the active WS
/// connection. Wave 4 `forward_ipc_to_sidecar` reads this — None while
/// disconnected, Some(sink) while the run loop holds an open socket.
///
/// Wrapped in `Arc<Mutex<Option<...>>>` so:
///   * Cloning the handle hands out cheap pointer-copies to async tasks.
///   * The run loop can swap the sink on reconnect.
///   * `#[tauri::command]` body can `lock().await` to send without
///     awaiting the whole loop.
#[derive(Default, Clone)]
pub struct WsClientHandle {
    pub tx: Arc<Mutex<Option<WsSink>>>,
}

/// Run the WS bus client forever. Reconnects with exponential backoff
/// 250 → 5000ms cap. On every connect, parks the SplitSink into the
/// managed `WsClientHandle` so the outbound command works.
pub async fn run_ws_client(app: AppHandle) {
    let handle = app.state::<WsClientHandle>().inner().clone();
    let mut backoff_ms: u64 = BACKOFF_START_MS;
    let mut consecutive_failures: u32 = 0;
    let mut emitted_unreachable: bool = false;
    loop {
        match connect_async(WS_URL).await {
            Ok((ws, _resp)) => {
                backoff_ms = BACKOFF_START_MS;
                consecutive_failures = 0;
                emitted_unreachable = false;
                app.emit("ws-state", "connected").ok();

                let (sink, mut stream) = ws.split();
                // Park the outbound sink so forward_ipc_to_sidecar can use it.
                {
                    let mut guard = handle.tx.lock().await;
                    *guard = Some(sink);
                }

                while let Some(msg) = stream.next().await {
                    match msg {
                        Ok(Message::Text(text)) => {
                            // Parse to extract envelope `type`; if parse fails
                            // emit on a generic channel so Wave 4 can surface
                            // schema drift without crashing the WS loop.
                            if let Ok(value) =
                                serde_json::from_str::<serde_json::Value>(text.as_ref())
                            {
                                // Tauri 2.x event names reject `:` and `.`; wire
                                // names like "ipc.session.snapshot" are routed
                                // on the Rust side as "ipc-session-snapshot".
                                // Listeners use the dashed form everywhere.
                                let event_name = ipc_event_name(&value);
                                app.emit(&event_name, value.clone()).ok();
                                if has_live_deck_context(&value) {
                                    app.emit("live-deck-context", value).ok();
                                }
                            } else {
                                app.emit("ipc-parse-error", text.to_string()).ok();
                            }
                        }
                        Ok(Message::Close(_)) => break,
                        Err(_) => break,
                        _ => {}
                    }
                }

                // Connection ended — drop the sink so subsequent calls
                // surface "WS not connected" instead of writing to a
                // dead socket.
                {
                    let mut guard = handle.tx.lock().await;
                    *guard = None;
                }
            }
            Err(_e) => {
                // Sidecar not up yet, or bus crashed — fall through to backoff.
                consecutive_failures = consecutive_failures.saturating_add(1);
            }
        }

        // Once we cross the threshold, latch an `unreachable` event so
        // the webview surfaces an actionable banner. We still keep
        // reconnecting in the background — recovery is automatic if the
        // sidecar comes back up — but the user sees the truth instead
        // of an endless "reconnecting…" status.
        if consecutive_failures >= UNREACHABLE_AFTER && !emitted_unreachable {
            app.emit("ws-state", "unreachable").ok();
            emitted_unreachable = true;
        } else if !emitted_unreachable {
            app.emit("ws-state", "reconnecting").ok();
        }
        tokio::time::sleep(Duration::from_millis(backoff_ms)).await;
        backoff_ms = (backoff_ms.saturating_mul(2)).min(BACKOFF_CAP_MS);
    }
}

/// Webview-callable forward: send an arbitrary ipc.* envelope to the
/// sidecar. Wave 4 wires the body — pulls the SplitSink from managed
/// state, serializes the JSON, sends.
///
/// Returns an error string if the WS is not connected (forwarded to the
/// TS client which surfaces it via Promise.reject + DevTools warning).
#[tauri::command]
pub async fn forward_ipc_to_sidecar(
    message: serde_json::Value,
    state: tauri::State<'_, WsClientHandle>,
) -> Result<(), String> {
    // Sidecar boot race (2026-05-21): the webview fires its startup IPC
    // (settings.get, status.recheck, profile load) the instant it mounts,
    // but the Rust WS client hasn't connected to the sidecar yet — the
    // sidecar takes a few seconds to bind :8765. Failing immediately with
    // "WS not connected" left the controller / profile / settings panels
    // stuck on their first-load error with no retry. Poll up to ~8s for the
    // run loop to park the sink. CRITICAL: release the lock between polls —
    // holding it across the sleep would deadlock the run loop that parks
    // the sink on connect. Connected = instant return on the first pass.
    forward_message_via_handle(message, state.inner(), 40, Duration::from_millis(200)).await
}

fn ipc_event_name(value: &serde_json::Value) -> String {
    if let Some(message_type) = value.get("type").and_then(|v| v.as_str()) {
        return message_type.replace('.', "-");
    }
    if value.get("course3_lens").is_some() {
        return "learn-course3-lens".into();
    }
    "unknown".into()
}

fn has_live_deck_context(value: &serde_json::Value) -> bool {
    value
        .get("deck_state")
        .and_then(|v| v.as_object())
        .is_some()
}

fn serialize_outbound_message(message: &serde_json::Value) -> Result<String, String> {
    serde_json::to_string(message).map_err(|e| e.to_string())
}

async fn forward_message_via_handle(
    message: serde_json::Value,
    handle: &WsClientHandle,
    attempts: usize,
    poll_delay: Duration,
) -> Result<(), String> {
    for _ in 0..attempts {
        {
            let mut guard = handle.tx.lock().await;
            if let Some(sink) = guard.as_mut() {
                let text = serialize_outbound_message(&message)?;
                return sink
                    .send(Message::Text(text.into()))
                    .await
                    .map_err(|e| e.to_string());
            }
        }
        tokio::time::sleep(poll_delay).await;
    }
    Err("forward_ipc_to_sidecar: WS not connected".into())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::net::TcpListener;
    use tokio::sync::oneshot;
    use tokio_tungstenite::accept_async;

    #[test]
    fn ipc_event_name_maps_learn_envelope_to_tauri_channel() {
        let value = serde_json::json!({
            "type": "ipc.learn.tutor_speak",
            "ts": "2026-05-28T00:00:00Z",
            "payload": {}
        });

        assert_eq!(ipc_event_name(&value), "ipc-learn-tutor_speak");
    }

    #[test]
    fn ipc_event_name_uses_unknown_for_missing_type() {
        let value = serde_json::json!({ "payload": { "music": 0.3 } });

        assert_eq!(ipc_event_name(&value), "unknown");
    }

    #[test]
    fn ipc_event_name_routes_flat_course3_lens_to_learn_channel() {
        let value = serde_json::json!({
            "music": 0.2,
            "audible": true,
            "course3_lens": {
                "session_active": true,
                "phrase_position_confidence": 0.92,
                "next_phrase_at": 64.0,
                "next_phrase_cue_id": "cue:track-a:break"
            }
        });

        assert_eq!(ipc_event_name(&value), "learn-course3-lens");
    }

    #[test]
    fn has_live_deck_context_routes_flat_deck_snapshot_to_library() {
        let value = serde_json::json!({
            "music": 0.2,
            "audible": true,
            "deck": "A",
            "deck_state": {
                "A": {"title": "Strobe", "confidence": 0.8}
            },
            "deck_mixer": {
                "connected": true,
                "xfader": 64,
                "A": {"vol": 110, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
            },
            "deck_source_context": concat!(
                "deck_source_context[identity_state=MusicState.deck_state ",
                "primary=nowplaying_controller_attribution_to_library_cache ",
                "resolved=A unresolved=B sources=folder_cache live_db=not_read ",
                "event_xml=diagnostic_only second_deck=independent_source_required ",
                "rule=unresolved_deck_is_not_transition_evidence]"
            ),
            "audio_delta": ["sub energy fell 50% (strong)"]
        });

        assert!(has_live_deck_context(&value));
        assert_eq!(ipc_event_name(&value), "unknown");
        assert_eq!(
            value.get("deck_source_context").and_then(|v| v.as_str()),
            Some(concat!(
                "deck_source_context[identity_state=MusicState.deck_state ",
                "primary=nowplaying_controller_attribution_to_library_cache ",
                "resolved=A unresolved=B sources=folder_cache live_db=not_read ",
                "event_xml=diagnostic_only second_deck=independent_source_required ",
                "rule=unresolved_deck_is_not_transition_evidence]"
            ))
        );
    }

    #[test]
    fn serialize_outbound_message_preserves_learn_ack_payload() {
        let message = serde_json::json!({
            "type": "ipc.learn.ack",
            "ts": "2026-05-28T00:00:00Z",
            "payload": {
                "control_id": "lesson_continue",
                "source": "click",
                "value": 127,
                "prev_value": 0,
                "direction": "down"
            }
        });

        let encoded = serialize_outbound_message(&message).expect("json serialization");
        let decoded: serde_json::Value =
            serde_json::from_str(&encoded).expect("encoded json should parse");

        assert_eq!(decoded, message);
    }

    #[tokio::test]
    async fn forward_message_via_handle_waits_for_sink_and_sends_learn_ack() {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind local ws test server");
        let addr = listener.local_addr().expect("local addr");
        let (received_tx, received_rx) = oneshot::channel();
        let server = tokio::spawn(async move {
            let (stream, _) = listener.accept().await.expect("accept ws client");
            let ws = accept_async(stream).await.expect("accept websocket");
            let (_sink, mut stream) = ws.split();
            if let Some(Ok(Message::Text(text))) = stream.next().await {
                received_tx.send(text.to_string()).ok();
            }
        });

        let handle = WsClientHandle::default();
        let helper_handle = handle.clone();
        let message = serde_json::json!({
            "type": "ipc.learn.ack",
            "ts": "2026-05-28T00:00:00Z",
            "payload": {
                "control_id": "lesson_continue",
                "source": "click",
                "value": 127,
                "prev_value": 0,
                "direction": "down"
            }
        });
        let helper_message = message.clone();
        let forward_task = tokio::spawn(async move {
            forward_message_via_handle(helper_message, &helper_handle, 20, Duration::from_millis(5))
                .await
        });

        tokio::time::sleep(Duration::from_millis(10)).await;
        let (ws, _) = connect_async(format!("ws://{addr}"))
            .await
            .expect("connect ws client");
        let (sink, _stream) = ws.split();
        {
            let mut guard = handle.tx.lock().await;
            *guard = Some(sink);
        }

        forward_task
            .await
            .expect("forward task should not panic")
            .expect("forward should send once sink appears");
        let received = received_rx
            .await
            .expect("server should receive a text frame");
        let decoded: serde_json::Value =
            serde_json::from_str(&received).expect("received json should parse");
        assert_eq!(decoded, message);
        server.await.expect("server task should finish");
    }
}
