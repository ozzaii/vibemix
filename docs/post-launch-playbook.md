# 72-Hour Post-Launch Playbook

> Hour-by-hour script for the first 72h after `git tag v0.1.0 && git push --tags`.
> Phase 20 Plan 20 Task 4.

## T+0:00 — Tag pushed

- [ ] `git tag v0.1.0` (signed: `git tag -s`)
- [ ] `git push origin main --tags`
- [ ] Verify GitHub Actions `release.yml` dispatched within 30s
- [ ] Open `Actions` tab; both `macos-14` and `windows-latest` jobs are queued or running
- [ ] Post in `#vibemix-rota`: `🟢 v0.1.0 dispatched — watching matrix`

## T+0:30 — Matrix completes

- [ ] Both jobs are green; no red X
- [ ] GitHub Release `v0.1.0` exists in **draft** mode
- [ ] DMG attached: `vibemix-0.1.0-mac.dmg`
- [ ] MSI attached: `vibemix-0.1.0-windows-installer.msi`
- [ ] `latest.json` attached
- [ ] `verify_binary.py` report attached + shows zero `AIza` matches

If matrix red: do **not** flip the Release to public. Diagnose in
`Actions` logs. Common: secret missing, notarization rejected, signing
identity expired.

## T+0:45 — Manual smoke test (Kaan, on dev Mac)

- [ ] Download the DMG from the draft Release
- [ ] Drag to Applications + launch
- [ ] First-run wizard completes
- [ ] One AI reaction plays
- [ ] If anything weird: pause, fix, retag as v0.1.1 (not the same tag).

## T+1:00 — Flip Release to public + announce

- [ ] GitHub Release: edit → uncheck "Set as a pre-release" → publish
- [ ] Drop the Release URL in Bravoh Discord `#announcements`
- [ ] Drop the Release URL in vibemix Discord `#announcements`
- [ ] Tweet from `@altidus_world` with the demo GIF
- [ ] If outreach list is ready, send the launch newsletter

## T+1:00 → T+8:00 — Launch day, Kaan primary

Every 30 minutes:
- [ ] Sweep `is:open is:issue label:triage` on GitHub
- [ ] Sweep new Discord messages
- [ ] Glance at `api.altidus.world` admin panel for cost-per-DAU + error rate
- [ ] Star count tick check (we want the first 100 to come fast)

If a critical bug surfaces:
1. Reproduce locally if possible.
2. Decide: hotfix-now vs. ride-it-out (workaround in pinned Discord message).
3. If hotfix: branch off `v0.1.0`, fix, tag `v0.1.1`, push. Matrix re-runs.

## T+8:00 → T+16:00 — Francesco

Same protocol. Document everything in Discord rota thread.

## T+16:00 → T+24:00 — Kaan

Same. End-of-day-1 retro start: jot what surprised you.

## T+24:00 → T+48:00 — Day 2 async

- [ ] 10:00 CET — 15-min Discord standup with rota team
- [ ] 4h SLA on `triage` labels
- [ ] No new feature work; only critical-bug hotfixes if needed
- [ ] Update README with anything that needs clarifying (FAQ
      additions based on Day-1 confusion patterns)

## T+48:00 → T+72:00 — Day 3 async

Same as day 2.

End of day 3: draft `docs/v0.1.0-launch-retro.md`. Sections:
- What broke
- What surprised us
- What the rota model needs to change
- Star + Discord growth as supporting data
- Top 3 things to fix in v0.1.1

## Common scenarios + responses

### "It says vibemix can't be opened because Apple cannot check it"
- Cert is valid but Gatekeeper hasn't accepted it yet on the user's machine.
- Tell them: right-click → Open → confirm dialog. Pin this in Discord.
- Long-term fix: investigate why notarization stapler didn't apply.

### "Windows Defender SmartScreen blocks the installer"
- SignPath OSS cert has low reputation initially. SmartScreen learns.
- Workaround: `More info` → `Run anyway`. Pin in Discord.
- Long-term: SmartScreen reputation builds over weeks of installs.

### "AI talks over me"
- Mic gating issue. Ask user to check Settings → Voice Gate ms (default 600).
- Pin a `Voice gate tuning` guide if 3+ reports come in.

### "AI says random stuff that isn't happening"
- Hallucination. Ask for `events.jsonl` from `~/.vibemix/sessions/<latest>/`.
- Triage: is it a controller-mapping miss (CC# wrong), an anti-slop
  template miss, or genuine grounding failure?
- If genuine grounding failure → Phase 16 ear-gate didn't catch this →
  it goes on the v0.1.1 list.

### "How do I uninstall?"
- macOS: drag from `/Applications` to trash.
- Windows: Settings → Apps → vibemix → Uninstall.
- Pin in FAQ.

### "Will you support [Linux / Rekordbox / Mixxx]?"
- Linux: no (v1 explicit). Mixxx + Rekordbox: v2 candidates.
- Point to `.planning/v2-roadmap.md` if/when public.

## Hotfix process (in-launch)

1. `git checkout -b hotfix/<one-word> main`
2. Fix on the branch
3. `git merge --ff-only main` (rebase if needed)
4. Bump version in `tauri.conf.json5` + `pyproject.toml`
5. Verify `pytest tests/repo tests/dist tests/reaction_reel`
6. Tag `v0.1.<N+1>`, push
7. Wait for matrix, smoke-test, flip Release, announce in Discord

## Retro template

Lives at `docs/v0.1.0-launch-retro.md` after T+72.

```
# v0.1.0 launch retro

## Numbers
- Stars (T+24): __  / target 100
- Stars (T+72): __  / target 250
- Discord members (T+72): __
- Issues opened (T+72): __
- Issues closed (T+72): __
- Critical bugs: __
- Hotfix releases: v0.1.1, v0.1.2, ...

## What worked
- ...

## What broke
- ...

## What surprised us
- ...

## v0.1.1 priorities (top 3)
1. ...
2. ...
3. ...
```
