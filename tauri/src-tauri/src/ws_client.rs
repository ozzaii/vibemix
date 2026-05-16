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
use tokio_tungstenite::{
    connect_async,
    tungstenite::Message,
    MaybeTlsStream,
    WebSocketStream,
};

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
                                let msg_type = value
                                    .get("type")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("unknown")
                                    .to_string();
                                // Tauri 2.x event names reject `:` and `.`; wire
                                // names like "ipc.session.snapshot" are routed
                                // on the Rust side as "ipc-session-snapshot".
                                // Listeners use the dashed form everywhere.
                                let event_name = msg_type.replace('.', "-");
                                app.emit(&event_name, value).ok();
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
    let mut guard = state.tx.lock().await;
    let Some(sink) = guard.as_mut() else {
        return Err("forward_ipc_to_sidecar: WS not connected".into());
    };
    let text = serde_json::to_string(&message).map_err(|e| e.to_string())?;
    sink.send(Message::Text(text.into()))
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}
