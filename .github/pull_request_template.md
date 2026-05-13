<!-- Thanks for the PR. Fill in the boxes below before requesting review. -->

## Summary

<!-- One paragraph: what changed and why. -->

## Linked issue

Closes #<issue-number>
<!-- Or: "Refs #<issue-number>" if this is partial work. -->

## Test plan

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added or updated tests
- [ ] Ran the local pytest suite (`source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`)
- [ ] Ran vitest if frontend changed (`cd tauri/ui && npx vitest run`)
- [ ] Ran `cargo check` if Rust changed
- [ ] Manually tested on my rig

## Breaking change?

- [ ] No
- [ ] Yes — describe migration path:

## DCO sign-off

- [ ] Every commit in this PR is signed off (`git commit -s`)
