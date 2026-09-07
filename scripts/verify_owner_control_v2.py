#!/usr/bin/env python3
"""Retired owner-control mutation entrypoint.

The historical version could mutate both Resort Core and DATABASE_URL while
providing CI credential fallbacks. Use verify_owner_control_v2_ci.py, which
requires explicit CI/test environment and localhost-only Core/PostgreSQL.
"""

raise SystemExit(
    "ERROR: scripts/verify_owner_control_v2.py is retired; use "
    "scripts/verify_owner_control_v2_ci.py only from guarded local CI/test."
)
