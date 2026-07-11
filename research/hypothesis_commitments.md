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
| h002 | eace9cd2180834d105bb45fd0b5a535ad0685ef872e95dc985fb2da47a9fbf3e | 2026-07-03 |
| h003 | 2d26ebb667fb11b7a60b4662a53f48fb8e18f39ddea076dda4229e978622d2fb | 2026-07-03 |
| h004 | 1a3d8d582d43ebc261757b889401d2525371442376444131b174ab46b5107c4b | 2026-07-03 |
| h005 | 751b76b8818ce41d2a3533d903ed5b0095fa29d6115aab18281728d4e15517a3 | 2026-07-03 |
| h006 | 9f0f40c7d1026a5e3fb80cfee35c36810022007ca413a723fbdef102497e8f94 | 2026-07-03 |
| h007 | 546a771f22e4f1b1a1e43265f9e58198cf7869a53c849c9c16063a082422383d | 2026-07-10 |
| h008 | 3f556dc5dc4f9c86ea6e99f712a3686a872e53f571a53aa146c9d962ae513c94 | 2026-07-11 |
