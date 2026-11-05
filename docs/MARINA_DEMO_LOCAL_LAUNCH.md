# MARINA SMART — local interactive demo

This is the existing MARINA SMART PMS, not a mockup. Uses the reviewed branch, synthetic rooms and an isolated Docker volume; no Three Crowns DB or domains.

## Ubuntu / macOS with Docker
```bash
git clone --branch fix/marina-staging-preflight-20261020 https://github.com/stvelikiy-star/resort-os.git marina-smart-demo
cd marina-smart-demo
bash scripts/marina_demo_start.sh
```
If the private repository is not accessible by HTTPS, authenticate with GitHub CLI then `gh repo clone stvelikiy-star/resort-os marina-smart-demo -- --branch fix/marina-staging-preflight-20261020`.

After Docker reports healthy, visit **http://127.0.0.1:13001** on the **same computer** and log in using the username/password printed by the script. Web: http://127.0.0.1:13000; Staff: http://127.0.0.1:13002. Only the owner role is created initially; no payments/providers/AI external API are enabled. 12 synthetic rooms/3 categories.

The database is persisted in Docker volume `marina_demo_db` and credentials in untracked `.marina-demo.env` (permissions 0600). Never share this file. If the demo database already contains properties, the seed process intentionally refuses to overwrite them; don't use `down -v` without an explicit choice to delete test data.

Stop: `docker compose --env-file .marina-demo.env -f compose.marina-demo.yaml down` (does not erase DB). Restart: `docker compose --env-file .marina-demo.env -f compose.marina-demo.yaml up -d`.

**Remote access:** localhost is private on purpose. To review from a separate device, use an authenticated SSH port forward or carefully configured Tailscale; do not publicly expose demo credentials, plain HTTP or raw PostgreSQL. This does **not** constitute public production deployment.
