# Legacy dining findings

The uploaded legacy prototype is treated as a UX/process reference only. Its Firebase/Firestore data model is intentionally not imported into Resort OS.

Useful concepts retained for implementation:
- daily meal calendar per staying guest;
- separate adult/child portions;
- breakfast/lunch/dinner production totals;
- departure-day meal boundary;
- chef production dashboard;
- guest/table/waiter linkage;
- waiter-specific table queue;
- conflict-safe table seating/moves;
- hall map/zones;
- offline read cache and push-ready notifications.

Security note: legacy credentials/config files must never be copied into Resort OS. Existing PostgreSQL, FastAPI auth, Stay/Reservation identity and audit logging remain authoritative.
