//! Ear-test release-gate log writer.
//!
//! The debrief window posts `write_ear_test_log { payload }` when Kaan signs
//! off a session for the hybrid hallucination gate. The Python writer remains
//! the source-of-truth for offline tooling; this command mirrors its schema
//! invariants so the desktop path writes the same `eval/ear-test-logs/*.json`
//! artifacts instead of calling an unregistered command.

use serde_json::{Map, Value};
use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

const EAR_TEST_LOG_DIR: &str = "eval/ear-test-logs";
const FREE_FORM_MAX_LEN: usize = 4000;
const DURATION_MIN_S: i64 = 1800;
const SLOP_FLAG_KEYS: [&str; 4] = ["felt_slop", "felt_scripted", "felt_late", "felt_generic"];
const GENRE_ENUM: [&str; 7] = [
    "hard_tek", "techno", "house", "hip_hop", "dnb", "dubstep", "other",
];
const REQUIRED_KEYS: [&str; 8] = [
    "session_id",
    "started_at",
    "duration_s",
    "genre",
    "slop_flags",
    "free_form",
    "signed_by",
    "signed_at",
];

#[tauri::command]
pub async fn write_ear_test_log(payload: Value) -> Result<String, String> {
    write_ear_test_log_to(payload, Path::new(EAR_TEST_LOG_DIR))
        .map(|path| path.to_string_lossy().to_string())
}

fn write_ear_test_log_to(payload: Value, base_dir: &Path) -> Result<PathBuf, String> {
    let obj = payload
        .as_object()
        .ok_or_else(|| "payload must be object".to_string())?;
    validate_payload(obj)?;

    let session_id = obj
        .get("session_id")
        .and_then(Value::as_str)
        .ok_or_else(|| "session_id missing".to_string())?;
    let out_path = base_dir.join(format!("{session_id}.json"));
    atomic_write_json(&out_path, &Value::Object(obj.clone()))?;
    Ok(out_path)
}

fn validate_payload(obj: &Map<String, Value>) -> Result<(), String> {
    let required: BTreeSet<&str> = REQUIRED_KEYS.into_iter().collect();
    let present: BTreeSet<&str> = obj.keys().map(String::as_str).collect();

    let missing: Vec<&str> = required.difference(&present).copied().collect();
    if !missing.is_empty() {
        return Err(format!("missing required keys: {missing:?}"));
    }
    let extra: Vec<&str> = present.difference(&required).copied().collect();
    if !extra.is_empty() {
        return Err(format!("unknown keys: {extra:?}"));
    }

    let session_id = require_str(obj, "session_id")?;
    validate_session_id(session_id)?;
    require_str(obj, "started_at")?;
    require_str(obj, "signed_at")?;

    let duration_s = obj
        .get("duration_s")
        .and_then(Value::as_i64)
        .ok_or_else(|| "duration_s must be integer".to_string())?;
    if duration_s < DURATION_MIN_S {
        return Err(format!("duration_s must be >= {DURATION_MIN_S}"));
    }

    let genre = require_str(obj, "genre")?;
    if !GENRE_ENUM.contains(&genre) {
        return Err(format!("genre not allowed: {genre}"));
    }

    let slop_flags = obj
        .get("slop_flags")
        .and_then(Value::as_object)
        .ok_or_else(|| "slop_flags must be object".to_string())?;
    let slop_required: BTreeSet<&str> = SLOP_FLAG_KEYS.into_iter().collect();
    let slop_present: BTreeSet<&str> = slop_flags.keys().map(String::as_str).collect();
    let slop_missing: Vec<&str> = slop_required.difference(&slop_present).copied().collect();
    if !slop_missing.is_empty() {
        return Err(format!("slop_flags missing keys: {slop_missing:?}"));
    }
    let slop_extra: Vec<&str> = slop_present.difference(&slop_required).copied().collect();
    if !slop_extra.is_empty() {
        return Err(format!("slop_flags unknown keys: {slop_extra:?}"));
    }
    for key in SLOP_FLAG_KEYS {
        if !slop_flags.get(key).is_some_and(Value::is_boolean) {
            return Err(format!("slop_flags.{key} must be bool"));
        }
    }

    let free_form = require_str(obj, "free_form")?;
    if free_form.chars().count() > FREE_FORM_MAX_LEN {
        return Err(format!("free_form too long: > {FREE_FORM_MAX_LEN}"));
    }

    if require_str(obj, "signed_by")? != "kaan" {
        return Err("signed_by must be 'kaan'".into());
    }

    Ok(())
}

fn require_str<'a>(obj: &'a Map<String, Value>, key: &str) -> Result<&'a str, String> {
    obj.get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("{key} must be string"))
}

fn validate_session_id(session_id: &str) -> Result<(), String> {
    let len = session_id.chars().count();
    if len == 0 || len > 64 {
        return Err("session_id length must be 1..64".into());
    }
    if !session_id
        .chars()
        .all(|ch| ch.is_ascii_alphanumeric() || ch == '_' || ch == '-')
    {
        return Err("session_id contains illegal characters".into());
    }
    Ok(())
}

fn atomic_write_json(path: &Path, value: &Value) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or_else(|| "ear-test output has no parent".to_string())?;
    fs::create_dir_all(parent).map_err(|e| format!("create ear-test dir failed: {e}"))?;

    let body = serde_json::to_vec_pretty(value).map_err(|e| format!("encode failed: {e}"))?;
    let tmp = path.with_extension(format!("json.{}.tmp", std::process::id()));
    fs::write(&tmp, body).map_err(|e| format!("temp write failed: {e}"))?;
    fs::rename(&tmp, path).map_err(|e| {
        let _ = fs::remove_file(&tmp);
        format!("atomic rename failed: {e}")
    })?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn valid_payload() -> Value {
        json!({
            "session_id": "20260528-221500",
            "started_at": "2026-05-28T22:15:00Z",
            "duration_s": 1800,
            "genre": "techno",
            "slop_flags": {
                "felt_slop": false,
                "felt_scripted": false,
                "felt_late": false,
                "felt_generic": false
            },
            "free_form": "",
            "signed_by": "kaan",
            "signed_at": "2026-05-28T22:45:00Z"
        })
    }

    #[test]
    fn rejects_traversal_session_id() {
        let mut payload = valid_payload();
        payload["session_id"] = json!("../escape");
        assert!(write_ear_test_log_to(payload, Path::new("unused")).is_err());
    }

    #[test]
    fn rejects_too_short_session() {
        let mut payload = valid_payload();
        payload["duration_s"] = json!(1799);
        assert!(write_ear_test_log_to(payload, Path::new("unused")).is_err());
    }

    #[test]
    fn writes_valid_payload_atomically() {
        let dir = tempfile::tempdir().unwrap();
        let out = write_ear_test_log_to(valid_payload(), dir.path()).unwrap();
        assert_eq!(out.file_name().unwrap(), "20260528-221500.json");
        let saved: Value = serde_json::from_slice(&fs::read(out).unwrap()).unwrap();
        assert_eq!(saved["signed_by"], "kaan");
        assert_eq!(saved["slop_flags"]["felt_generic"], false);
    }
}
