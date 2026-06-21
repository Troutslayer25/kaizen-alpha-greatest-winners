# Sealed-Hypothesis Commitments

Pre-data priors are sealed BEFORE discovery so they cannot pollute Phases 0-A4, yet are
timestamp-proven to predate the data (this file's git commit time = precedence proof). Each
entry is an opaque ID + the SHA-256 of the private plaintext (kept local/gitignored at
`research/hypotheses/sealed/`, never pushed). At Phase B3 the plaintext is revealed and
re-hashed; a match proves the prior was committed before any data was seen. Opaque IDs reveal
no subject, so even this committed file cannot bias discovery.

Verify: `sha256sum research/hypotheses/sealed/<id>.md`

| ID | SHA-256 | Sealed (UTC date) |
|---|---|---|
| h001 | 435fabe2d81b2826b4fbca8ab9c133afa1fecbb8d8a3b0b79efb9457a26b36c9 | 2026-06-21 |
