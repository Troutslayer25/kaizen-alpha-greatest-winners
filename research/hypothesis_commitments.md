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
| h007 | 87ec01ea51d039fb8058670f16f018124c4c69555a1e94effba5dc1514b6a68c | 2026-07-10, restructured 2026-07-12 |
| h008 | 63a215ad126a7a1ec34bd191572833cbcf1c732147d52c5e201b78b1b91a5496 | 2026-07-11, restructured 2026-07-12 |
| h009 | 23051f151093947573e7ed4a3af12d22c8e22e2efd5b9bccd45880307cfe4bbd | 2026-07-11, restructured 2026-07-12 |
| h010 | 5d072977c5b691da0af47f14fb5b1f0ecc9b16b488b716eaf439cd2dc8c91707 | 2026-07-11, restructured 2026-07-12 |
| h011 | c3f505968a369dda0a9b156c9f4256a4007a65e1fba18979cd3de02d7ab3a4b1 | 2026-07-12 |

h007–h010 were restructured 2026-07-12 into the standard template (sub-hypotheses, failure
hypothesis, null, acceptance/success criteria) — pre-data, content-preserving; directional
bets unchanged. Original hashes remain in git history (commits 6bb7288, d9d4d0f, d4aa903) as
the earlier precedence proof; the current hashes above are authoritative for B3 verification.
