# FLEX defect register
Owner roadmap edition 1.0; work strictly in current stage. CODE READY is not TEST PASS.
 
| ID | Priority | Finding and reproduction | Status / action |
|---|---|---|---|
| FLEX-018 | P0 | New simulation module absent from deployment bundle completeness and parity test list at integration SHA 128ba9e3. | CODE READY: 7f8e5a4, ceb4b710. Six module hashes match; exact final draft CI still required. |
| FLEX-019 | P0 | No direct entrypoint test matrix for enabled QA / disabled QA / non-QA registration of simulation, journal and acceptance routes. | CODE READY: ceb4b710 adds negative and positive registration contracts; CI required. |
| FLEX-020 | P0 | Divergent legacy PR #590 includes separate recovery flow, older read-only catalogue and UX logic; behavioral equivalence not fully verified. | IN PROGRESS: preserve branch, compare residual changed files and verify current supported behavior. No blind merge. |
| FLEX-021 | P1 | PR #588 differs in old session bridge/UI lines; newer session binding exists. | IN PROGRESS: preserve branch, targeted session regression; do not overwrite newer auth. |
| FLEX-001 | P0 | Cloud QA historically older than integration. | NOT STARTED in this stage; Stage 2. |
| FLEX-002 | P0 | Active migration registry historically 21; 22–25 pending. | Stage 1/2; separate approval required. |
| FLEX-003 | P0 | Acceptance writer runtime membership missing in last inspection. | Stage 1/2; separately reviewed grant. |
| FLEX-004 | P0 | Password-mode owner acceptance requires compatibility review. | Stage 2; do not modify active authentication. |
| FLEX-005 | P0 | No verified active cloud owner fixture. | Stage 2. |
| FLEX-006 | P0 | Subscription lifecycle incomplete. | Stage 3. |
| FLEX-007 | P0 | Test invoice issuance incomplete. | Stage 4; real issuance frozen. |
| FLEX-008 | P0 | Full two-hotel financial cycle not accepted in cloud. | Stage 4. |
| FLEX-009 | P0 | Launch offer paid finalization incomplete. | Stage 3/4; actual payments frozen. |
| FLEX-010 | P0 | Independent restore of current cloud QA not verified. | Stage 1. |
| FLEX-011 | P1 | Credit can remain alongside debt after refund; explicit credit application needed. | Stage 4. |
| FLEX-012 | P1 | Additional SQL constraints for synthetic journal operation sequence/refund limits require review. | Stage 4. |
| FLEX-013–015 | P1 | Agent, investor, partner workflows incomplete. | Stage 5. |
| FLEX-016 | P1 | Commercial analytics incomplete. | Stage 6. |
| FLEX-017 | P1 | Full cloud role/language/theme/viewport matrix not accepted. | Stage 8/9. |
 
No defect closed merely because code exists. No unrelated repo or active cloud changes authorized by this record.
