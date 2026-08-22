# Resort OS

Universal Hospitality / Resort Operating System.

## Repository status

BOOTSTRAP BASELINE.

This repository was created after source-discovery failed to locate a
complete prior Guest House / Resort OS implementation.

The repository MUST NOT claim that a production PMS already exists.

## Canonical Knowledge

The `knowledge/` directory contains the six canonical Resort OS documents:

- 00_PRODUCT_BIBLE.md
- 01_DOMAIN_BUSINESS_RULES.md
- 02_SYSTEM_ARCHITECTURE.md
- 03_AI_ADMIN.md
- 04_CURRENT_STATE.md
- 05_DECISIONS_AND_BACKLOG.md

`04_CURRENT_STATE.md` is the only canonical owner of factual implementation
reality.

UNKNOWN / VALIDATE states must not be promoted without evidence.

## Recovery artifacts

`recovery-artifacts/` contains historical UI/code fragments recovered from
local archives.

Recovery artifacts are evidence/reference only.

They are NOT automatically considered:
- production code;
- implemented functionality;
- verified functionality;
- approved architecture.

## Development rule

KNOWLEDGE
→ CURRENT STATE
→ GAP
→ PRIORITY
→ IMPLEMENT
→ TEST
→ EVIDENCE
→ VERIFIED / NOT VERIFIED
→ CURRENT STATE UPDATE

No production deploy, payment activation, destructive DB operation, or
irreversible production action without an explicit owner gate.
