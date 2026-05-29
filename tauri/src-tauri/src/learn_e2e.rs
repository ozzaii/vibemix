// SPDX-License-Identifier: Apache-2.0
//! Opt-in launched Learn smoke helpers.
//!
//! macOS has no official Tauri WebDriver path for WKWebView. This module keeps
//! the launched-app proof local and inert by default: when the e2e env flag is
//! set, the Rust shell opens the real Learn window and injects a small script
//! that clicks the same controls a beginner would click. The Python harness on
//! :8765 remains the verifier by persisting Learn progress.

use std::fs;
use std::path::PathBuf;
use std::time::Duration;

use tauri::{AppHandle, Manager};

use crate::learn_window::{open_learn_window, LEARN_WINDOW_LABEL};

pub const E2E_EXTERNAL_SIDECAR_ENV: &str = "VIBEMIX_E2E_EXTERNAL_SIDECAR";
pub const E2E_AUTORUN_LEARN_ENV: &str = "VIBEMIX_E2E_AUTORUN_LEARN";
pub const E2E_RESULT_PATH_ENV: &str = "VIBEMIX_E2E_RESULT_PATH";
pub const E2E_AXE_PATH_ENV: &str = "VIBEMIX_E2E_AXE_PATH";

pub fn external_sidecar_enabled() -> bool {
    flag_enabled(std::env::var(E2E_EXTERNAL_SIDECAR_ENV).ok())
}

#[tauri::command]
pub fn record_learn_e2e_result(payload: serde_json::Value) -> Result<(), String> {
    if !flag_enabled(std::env::var(E2E_AUTORUN_LEARN_ENV).ok()) {
        return Err("learn e2e recorder disabled".into());
    }
    let path = std::env::var(E2E_RESULT_PATH_ENV)
        .map(PathBuf::from)
        .map_err(|_| "learn e2e result path not configured".to_string())?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| format!("result dir: {err}"))?;
    }
    let encoded = serde_json::to_vec_pretty(&payload).map_err(|err| err.to_string())?;
    fs::write(&path, encoded).map_err(|err| format!("result write: {err}"))?;
    Ok(())
}

pub fn install_learn_autorun(app: &AppHandle) {
    if !flag_enabled(std::env::var(E2E_AUTORUN_LEARN_ENV).ok()) {
        return;
    }

    let app = app.clone();
    tauri::async_runtime::spawn(async move {
        if let Err(err) = run_learn_autorun(app).await {
            tracing::error!("learn e2e autorun failed: {err}");
        }
    });
}

async fn run_learn_autorun(app: AppHandle) -> Result<(), String> {
    tokio::time::sleep(Duration::from_millis(1200)).await;
    open_learn_window(app.clone()).await?;
    tokio::time::sleep(Duration::from_millis(1600)).await;
    let window = app
        .get_webview_window(LEARN_WINDOW_LABEL)
        .ok_or_else(|| "learn window missing after open".to_string())?;
    if let Ok(axe_path) = std::env::var(E2E_AXE_PATH_ENV) {
        let axe_source =
            fs::read_to_string(&axe_path).map_err(|err| format!("axe source read: {err}"))?;
        window
            .eval(axe_source)
            .map_err(|err| format!("axe source eval: {err}"))?;
    }
    window
        .eval(learn_autorun_script())
        .map_err(|err| format!("learn autorun eval: {err}"))?;
    tracing::info!("learn e2e autorun injected");
    Ok(())
}

fn flag_enabled(value: Option<String>) -> bool {
    matches!(
        value.as_deref(),
        Some("1") | Some("true") | Some("TRUE") | Some("yes") | Some("YES")
    )
}

pub fn learn_autorun_script() -> &'static str {
    r##"
(() => {
  if (window.__vibemixLearnE2EStarted === true) return;
  window.__vibemixLearnE2EStarted = true;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const checks = [];
  const failures = [];
  const pass = (name, detail = {}) => checks.push({ name, ok: true, ...detail });
  const fail = (name, detail = {}) => {
    checks.push({ name, ok: false, ...detail });
    failures.push({ name, ...detail });
  };
  const assertCheck = (name, condition, detail = {}) => {
    if (condition) pass(name, detail);
    else fail(name, detail);
  };
  const text = (selector) => {
    const node = document.querySelector(selector);
    return node?.textContent?.trim() ?? "";
  };
  const isRendered = (node) => {
    if (!node) return false;
    if (node instanceof HTMLElement && node.hidden) return false;
    let current = node;
    while (current) {
      if (current instanceof HTMLElement || current instanceof SVGElement) {
        const style = getComputedStyle(current);
        if (style.display === "none" || style.visibility === "hidden") return false;
      }
      current = current.parentElement;
    }
    return true;
  };
  const visibleButton = (selector) => {
    const node = document.querySelector(selector);
    if (!(node instanceof HTMLButtonElement)) return null;
    if (!isRendered(node) || node.disabled) return null;
    return node;
  };
  const rgb = (value) => {
    const raw = String(value).trim();
    const hex = raw.match(/^#([0-9a-f]{6})$/i);
    if (hex) {
      return {
        r: Number.parseInt(hex[1].slice(0, 2), 16),
        g: Number.parseInt(hex[1].slice(2, 4), 16),
        b: Number.parseInt(hex[1].slice(4, 6), 16),
        a: 1,
      };
    }
    const match = raw.match(/^rgba?\(([^)]+)\)$/i);
    if (!match) return null;
    const parts = match[1].split(",").map((part) => Number.parseFloat(part.trim()));
    return { r: parts[0], g: parts[1], b: parts[2], a: parts[3] ?? 1 };
  };
  const srgb = (v) => {
    const n = v / 255;
    return n <= 0.03928 ? n / 12.92 : Math.pow((n + 0.055) / 1.055, 2.4);
  };
  const luminance = (c) => 0.2126 * srgb(c.r) + 0.7152 * srgb(c.g) + 0.0722 * srgb(c.b);
  const contrast = (a, b) => {
    const hi = Math.max(luminance(a), luminance(b));
    const lo = Math.min(luminance(a), luminance(b));
    return (hi + 0.05) / (lo + 0.05);
  };
  const colorOf = (selector) => rgb(getComputedStyle(document.querySelector(selector)).color);
  const tokenColor = (name) => rgb(getComputedStyle(document.documentElement).getPropertyValue(name));
  const recordProof = async () => {
    if (window.axe?.run) {
      const axeResult = await window.axe.run(document, {
        runOnly: {
          type: "tag",
          values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
        },
      });
      const violations = axeResult.violations
        .filter((violation) => violation.impact === "critical" || violation.impact === "serious")
        .map((violation) => ({
          id: violation.id,
          impact: violation.impact,
          nodes: violation.nodes.map((node) => node.target.join(" ")).slice(0, 5),
        }));
      assertCheck("axe-core serious violations", violations.length === 0, { violations });
    } else {
      fail("axe-core injected", { reason: "window.axe missing" });
    }
    const payload = {
      ok: failures.length === 0,
      checks,
      failures,
      href: location.href,
      userAgent: navigator.userAgent,
      ts: new Date().toISOString(),
    };
    const mod = await import("/src/tauri-runtime.ts");
    await mod.invokeTauri("record_learn_e2e_result", { payload });
    if (failures.length > 0) {
      throw new Error(`learn e2e quality failures: ${JSON.stringify(failures)}`);
    }
  };
  const waitFor = async (label, fn, timeoutMs = 30000) => {
    const started = performance.now();
    while (performance.now() - started < timeoutMs) {
      const value = fn();
      if (value) return value;
      await sleep(80);
    }
    throw new Error(`timed out waiting for ${label}`);
  };

  (async () => {
    await waitFor("learn root", () => document.querySelector("#learn-root"));
    await waitFor(
      "practice deck",
      () => document.querySelector("svg.learn-controller-schematic"),
    );
    await sleep(1800);

    const ids = Array.from(document.querySelectorAll("[id]")).map((node) => node.id);
    const duplicateIds = ids.filter((id, index) => ids.indexOf(id) !== index);
    assertCheck("no duplicate ids", duplicateIds.length === 0, { duplicateIds });

    const visibleButtons = Array.from(document.querySelectorAll("button")).filter(isRendered);
    const unnamedButtons = visibleButtons
      .map((button) => ({
        id: button.id,
        text: button.textContent?.trim() ?? "",
        ariaLabel: button.getAttribute("aria-label")?.trim() ?? "",
        title: button.getAttribute("title")?.trim() ?? "",
      }))
      .filter((button) => !button.text && !button.ariaLabel && !button.title);
    assertCheck("visible buttons have names", unnamedButtons.length === 0, { unnamedButtons });
    assertCheck(
      "practice map is opt-in",
      document.querySelector("#learn-progress-list-host")?.dataset.visible === "false" &&
        document.querySelector("#learn-progress-list-host")?.getAttribute("aria-hidden") === "true",
    );
    assertCheck(
      "booth frontstage is calm",
      document.querySelector("#learn-booth-panel")?.dataset.visible === "true" &&
        visibleButtons.length <= 3,
      { visibleButtonCount: visibleButtons.length },
    );

    const hiddenFocusable = Array.from(document.querySelectorAll("[aria-hidden='true']")).flatMap(
      (container) =>
        Array.from(
          container.querySelectorAll(
            "a[href],button,input,select,textarea,[tabindex]:not([tabindex='-1'])",
          ),
        )
          .filter((node) => !node.hasAttribute("disabled"))
          .filter(isRendered)
          .map((node) => ({ containerId: container.id, id: node.id, text: node.textContent?.trim() ?? "" })),
    );
    assertCheck("no visible focus targets inside aria-hidden", hiddenFocusable.length === 0, {
      hiddenFocusable,
    });

    const badControls = Array.from(
      document.querySelectorAll("svg.learn-controller-schematic [data-control-id]"),
    )
      .filter(isRendered)
      .map((node) => ({
        controlId: node.getAttribute("data-control-id"),
        role: node.getAttribute("role"),
        tabIndex: node.getAttribute("tabindex"),
        label: node.getAttribute("aria-label")?.trim() ?? "",
      }))
      .filter((node) => node.role !== "button" || node.tabIndex !== "0" || node.label.length === 0);
    assertCheck("controller controls are keyboardable buttons", badControls.length === 0, {
      badControls: badControls.slice(0, 5),
    });

    const start = await waitFor(
      "recommended lesson button",
      () => visibleButton("#learn-start-recommended"),
    );
    start.click();

    const expectedLines = [
      "Hello vibemix, what are you?",
      "I'm the best DJ app in the world.",
      "If you are the best, then who the fuck am I?",
      "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go.",
    ];

    for (const expected of expectedLines) {
      await waitFor(
        `tutor line ${expected}`,
        () => text(".tutor-dock .now") === expected,
      );
      const nowColor = colorOf(".tutor-dock .now");
      const voidColor = tokenColor("--void");
      assertCheck(
        "tutor line contrast clears AAA",
        nowColor !== null && voidColor !== null && contrast(nowColor, voidColor) >= 7,
        { expected },
      );
      const action = await waitFor(
        "continue action",
        () => visibleButton("#learn-screen-action"),
      );
      assertCheck(
        "screen action text fits",
        action.scrollWidth <= action.clientWidth + 1,
        { text: action.textContent?.trim() ?? "" },
      );
      action.click();
      await sleep(140);
    }

    await waitFor(
      "completed booth",
      () => document.querySelector("#learn-booth-panel")?.dataset.visible === "true",
      45000,
    );
    const nextPractice = await waitFor(
      "next recommended lesson",
      () => visibleButton("#learn-start-recommended"),
    );
    assertCheck(
      "booth recommends the next lesson after completion",
      /start\s+meet\s+your\s+controller/i.test(nextPractice.textContent ?? ""),
      { text: nextPractice.textContent?.trim() ?? "" },
    );
    assertCheck(
      "practice map remains opt-in after completion",
      document.querySelector("#learn-progress-list-host")?.dataset.visible === "false" &&
        document.querySelector("#learn-progress-list-host")?.getAttribute("aria-hidden") === "true",
    );
    await recordProof();
    console.info("[learn-e2e] completed beginner opening path");
  })().catch(async (err) => {
    fail("autorun completed without script error", { error: String(err?.message ?? err) });
    try {
      await recordProof();
    } catch {
      // The first error above is the signal; avoid masking it in DevTools.
    }
    console.error("[learn-e2e] failed", err);
  });
})();
"##
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn e2e_flags_are_explicit_opt_in() {
        assert!(flag_enabled(Some("1".to_string())));
        assert!(flag_enabled(Some("true".to_string())));
        assert!(flag_enabled(Some("yes".to_string())));
        assert!(!flag_enabled(None));
        assert!(!flag_enabled(Some("0".to_string())));
        assert!(!flag_enabled(Some("learn".to_string())));
    }

    #[test]
    fn autorun_script_uses_real_learn_controls() {
        let script = learn_autorun_script();
        assert!(script.contains("#learn-start-recommended"));
        assert!(script.contains("#learn-screen-action"));
        assert!(script.contains(".tutor-dock .now"));
        assert!(script.contains("click()"));
        assert!(script.contains("Hello vibemix, what are you?"));
        assert!(script.contains("record_learn_e2e_result"));
        assert!(script.contains("visible buttons have names"));
        assert!(script.contains("axe-core serious violations"));
        assert!(script.contains("booth recommends the next lesson after completion"));
        assert!(script.contains("practice map remains opt-in after completion"));
    }
}
