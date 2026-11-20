# MARINA SMART — Ubuntu server for 10–20 independent hotels

## Ground rules
- Existing ASUS Ubuntu has previously hosted AI PROF KG control center / n8n and is **not** verified online in this conversation. No actual Ubuntu changes have been made through this work.
- Approved product is the real MARINA SMART repository, not a new UI. Do not alter Three Crowns or its DB volume.
- `compose.marina-fleet.yaml` currently implements an **isolated staging per-hotel topology**, NOT a claim that the Ubuntu laptop is production-capable for 20 active hotels.
- Each hotel stack has its own database container + named Docker volume, API, web, admin, staff and migration/seed jobs. Its env is kept in `.marina-fleet/<slug>.env`, mode 0600, directory 0700. Each project's bridge network is automatically isolated by Compose. No PostgreSQL or API ports are published; three UI ports bind only to 127.0.0.1.
- This intentionally uses property-pinned single-hotel runtime until shared multi-tenant mode is rigorously verified. There is NO automatic cross-hotel data access.

## First: inspect hardware and existing services (read-only)
```bash
bash scripts/marina_ubuntu_preflight.sh
```
Evaluate free RAM/CPU, SSD/disk, Docker health, Tailscale, connectivity, network, power/UPS and available port ranges. Do not disturb existing systemd services, n8n, or network tunnels.

## First synthetic hotel pilot
```bash
python3 scripts/marina_fleet.py create hotel01 --port-base 15000
python3 scripts/marina_fleet.py start hotel01
python3 scripts/marina_fleet.py status hotel01
```
Open **http://127.0.0.1:15001** on Ubuntu (web 15000, staff 15002). Owner username and secret are in `.marina-fleet/hotel01.env` (never upload/share; retrieve locally). The generated hotel uses **synthetic** rooms/rates only and cannot be used to write real guest data safely.

## Second synthetic hotel isolation test
```bash
python3 scripts/marina_fleet.py create hotel02 --port-base 15010
python3 scripts/marina_fleet.py start hotel02
```
Second admin is local port 15011. Both have different databases, property IDs, network namespaces, volume names, owner credentials and ports.

## Backup and stop
```bash
python3 scripts/marina_fleet_backup.py hotel01
python3 scripts/marina_fleet.py stop hotel02
```
Stopping a hotel does not erase its database volume. **Do not run `docker compose down -v`** on hotels. Backup files are local and unencrypted until sent to approved encrypted offsite storage; verify restore separately before accepting a production hotel.

## Remote access
Never expose port 5432, 8000, 15000–15999 or `.env` files to public Internet. Tailscale or a verified HTTPS reverse proxy must be configured with per-hotel access controls. Plain HTTP is acceptable solely via local machine/private authenticated tunnel, not public. A public demo needs TLS, strong passwords, source verification and HTTP proxy/cookie security review.

## Capacity planning for 10–20
One full isolated stack per hotel uses multiple container processes and separate PostgreSQL, so 10–20 stacks will **not** be assumed safe on an ASUS laptop. Start with ONE test hotel, monitor idle/peak CPU, RAM, IOPS and p95 latency; add a second, then 5, 10, 20 only after measured load tests and restore exercises. Confirm hardware, power, storage and upstream upload capacity. For commercial production, likely move DB to encrypted managed PostgreSQL, consolidate stateless frontend hosting and use a VPS cluster/standby; require capacity and financial signoff. An Ubuntu notebook is an appropriate lab/pilot, not by itself a guaranteed 20-hotel SLA.

## Production gates
1. Staging source SHA approved, branch reconciliation and CI green (including 2-property and ordinary bookings).
2. Role matrix, MARINA AI live context, HOLD, seasons, concurrency, mobile and localization browser acceptance.
3. Dedicated backup cadence, encrypted offsite copy + tested isolated restore.
4. HTTPS, WSS, DNS, firewalls, OS patch policy, monitoring, UPS and controlled access.
5. Site-owner approval before real data and any automated payment/provider sync.
