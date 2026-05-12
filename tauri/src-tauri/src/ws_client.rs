//! Phase 11 Wave 2 — WS bus client.
//!
//! Connects to `ws://127.0.0.1:8765` (the Python sidecar's existing
//! `vibemix.runtime.ws_bus` from Phase 4) and forwards every inbound
//! `Message::Text` payload to the webview as `ipc:<type>` via
//! `tauri::Emitter`. Webview never opens its own socket — RESEARCH
//! anti-pattern §"Webview hardcoded localhost".
//!
//! Reconnects with exponential backoff 250 ms → 5000 ms cap.
//!
//! Validation rule (per plan): we do NOT validate the schema here —
//! Python validates on serialize, webview validates on receive via ajv
//! (Wave 0). Double validation in Rust adds latency without value.

use std::time::Duration;

use futures_util::StreamExt;
use tauri::{AppHandle, Emitter};
use tokio_tungstenite::{connect_async, tungstenite::Message};

const WS_URL: &str = "ws://127.0.0.1:8765";
const BACKOFF_START_MS: u64 = 250;
const BACKOFF_CAP_MS: u64 = 5000;

pub async fn run_ws_client(app: AppHandle) {
    let mut backoff_ms: u64 = BACKOFF_START_MS;
    loop {
        match connect_async(WS_URL).await {
            Ok((mut ws, _resp)) => {
                backoff_ms = BACKOFF_START_MS;
                app.emit("ws-state", "connected").ok();

                while let Some(msg) = ws.next().await {
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
                                    .unwrap_or("unknown");
                                app.emit(&format!("ipc:{msg_type}"), value).ok();
                            } else {
                                app.emit("ipc:parse-error", text.to_string()).ok();
                            }
                        }
                        Ok(Message::Close(_)) => break,
                        Err(_) => break,
                        _ => {}
                    }
                }
            }
            Err(_e) => {
                // Sidecar not up yet, or bus crashed — fall through to backoff.
            }
        }

        app.emit("ws-state", "reconnecting").ok();
        tokio::time::sleep(Duration::from_millis(backoff_ms)).await;
        backoff_ms = (backoff_ms.saturating_mul(2)).min(BACKOFF_CAP_MS);
    }
}

/// Webview-callable forward: send an arbitrary ipc.* envelope back to the
/// sidecar. Wave 4 wires the body (needs a managed WsClientHandle with the
/// outbound `SinkExt` half held in the run loop). Wave 2 publishes the
/// command so the capability allowlist locks at this wave.
#[tauri::command]
pub async fn forward_ipc_to_sidecar(_message: serde_json::Value) -> Result<(), String> {
    Err("forward_ipc_to_sidecar: not yet wired (Wave 4)".into())
}
