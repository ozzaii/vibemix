# Copy Substitutions

Forbidden tokens and preferred substitutions for vibemix copy.

Sourced by `scripts/launch/check_no_ai_slop.py` (parent contract,
`AI_SLOP_BLOCKLIST` constant) and Phase 49 sibling
`scripts/audit/check_no_slop_install.py` (installer + wizard surface).
The sibling imports the parent's blocklist constant directly — it does
NOT widen the parent's pinned target paths.

## Substitution table

| Forbidden | Preferred | Rationale |
|-----------|-----------|-----------|
| seamless | one-tap | "seamless" is AI marketing slop; "one-tap" is verifiable |
| seamlessly | (rewrite) | Same as above; never sneaks past the regex |
| robust | tested | "robust" hides "not measured" |
| leverage | use | "leverage" is consultant-speak; "use" is direct |
| intuitive | clear | "intuitive" claims user feeling without evidence |
| powerful | fast / specific | "powerful" hides "we don't know what makes this good" |
| delightful | good / useful | "delightful" is theatre |
| AI-powered | Gemini-grounded | vibemix is Gemini-only; specificity is anti-slop |
| smart | responsive / observant | "smart" hides "we trained nothing on your data" |
| next-generation | (rewrite) | Forbidden; never excuses absence of detail |
| deeply (anything) | (rewrite) | Regex `\bdeeply\s+\w+` is hard-banned |
| revolutionize | (rewrite) | Forbidden; never describes a utility |
| unleash | use / start | Forbidden; never describes a normal action |
| unlock | (rewrite) | Forbidden in product copy |
| synergize | (rewrite) | Buzzword |
| game-changer | (rewrite) | Hype |
| cutting-edge | (rewrite) | Hype |
| harness the power | (rewrite) | AI marketing default pattern |
| transformative | (rewrite) | Hype |
| paradigm | (rewrite) | Buzzword |

## How this file is consumed

- `scripts/launch/check_no_ai_slop.py` defines its `AI_SLOP_BLOCKLIST`
  constant. This file is the human-readable companion + suggestion source
  used by the sibling checker to surface preferred replacements.
- `scripts/audit/check_no_slop_install.py` (Phase 49 sibling) reads this
  file at run-time to look up preferred substitutions when reporting hits.

## Adding new entries

1. Add a row to the table above with rationale.
2. If the token is a regex (e.g., `\bdeeply\s+\w+`), document the regex
   form in the Forbidden column.
3. Update `scripts/launch/check_no_ai_slop.py § AI_SLOP_BLOCKLIST` to
   include the new literal.
4. Re-run the parent check + sibling checks to verify the new entry
   catches the intended copy.

## NOT a vibemix vocabulary

This list is anti-AI-slop, not anti-energy. Words like "fast", "live",
"ready", "tested", "audible", "responsive", "grounded" are encouraged.
The rule isn't blandness — it's refusing AI marketing default patterns.

## Phase 49 sibling-script invariant

The Phase 49 sibling at `scripts/audit/check_no_slop_install.py` is the
pattern Phase 47/48 established: each phase that needs anti-slop on a new
surface creates a sibling script that imports the parent's blocklist
constant. The parent's pinned target paths are CONTRACT and must not be
widened across phases.
