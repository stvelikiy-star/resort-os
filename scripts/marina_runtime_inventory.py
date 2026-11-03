#!/usr/bin/env python3
"""Read-only MARINA runtime inventory. No credentials, deployments or DB writes."""
import json
import os
from pathlib import Path
import shutil
import subprocess


def command(args, *, input_text=None, timeout=20):
    result = subprocess.run(args, input=input_text, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        # Do not print Docker/psql stderr, environment, or command exceptions.
        raise RuntimeError('READ_FAILED')
    return result.stdout.strip()


INSPECT = r'''{"name":{{json .Name}},"image_id":{{json .Image}},"status":{{json .State.Status}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"working_dir":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}},"compose_files":{{json (index .Config.Labels "com.docker.compose.project.config_files")}},"mounts":{{json .Mounts}},"ports":{{json .NetworkSettings.Ports}}}'''

API_PROBE = '''import json, os, urllib.request
keys = ('APP_ENV','PROPERTY_CODE','COOKIE_SECURE','MARINA_TENANT_CONTEXT_ENABLED',
        'MARINA_FLEET_CONFIRM','MARINA_DEMO_CONFIRM','ENABLE_GREEN_API_CONNECTION',
        'GREEN_API_PROPERTY_CODE','OPENAI_MARINA_ASSISTANT_MODEL')
data = {k: os.environ.get(k) for k in keys}
data['openai_key_present'] = bool(os.environ.get('OPENAI_API_KEY'))
data['green_credentials_present'] = all(os.environ.get(k) for k in
    ('GREEN_API_URL','GREEN_API_ID_INSTANCE','GREEN_API_TOKEN_INSTANCE'))
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5) as response:
        data['ready_http'] = response.status
except Exception:
    data['ready_http'] = 'unavailable'
print(json.dumps(data))
'''

# PostgreSQL enforces read-only execution even if the SQL is edited later.
PSQL = 'PGPASSWORD="$POSTGRES_PASSWORD" PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=5000" exec psql -X -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
DB_PROBE = '''SELECT json_build_object(
 'properties',(SELECT count(*) FROM properties),
 'rooms',(SELECT count(*) FROM rooms),
 'staff',(SELECT count(*) FROM staff_users),
 'reservations',(SELECT count(*) FROM reservations),
 'tasks',(SELECT count(*) FROM operational_tasks),
 'migrations',(SELECT count(*) FROM _prisma_migrations),
 'unfinished_migrations',(SELECT count(*) FROM _prisma_migrations WHERE finished_at IS NULL AND rolled_back_at IS NULL),
 'recent_migrations',(SELECT json_agg(x) FROM
   (SELECT migration_name,finished_at IS NOT NULL AS finished,rolled_back_at IS NOT NULL AS rolled_back
    FROM _prisma_migrations ORDER BY started_at DESC LIMIT 5) x));
'''


def main():
    report = {'mode': 'READ_ONLY', 'production_designation': 'NOT_INFERRED_FROM_CONTAINER_NAMES',
              'containers': [], 'checkouts': []}
    report['host'] = {'cpu_count': os.cpu_count(), 'free_disk_gib': round(shutil.disk_usage(Path.home()).free / 2**30, 1)}
    try:
        ids = command(['docker', 'ps', '-aq', '--filter', 'name=marina-']).split()
    except Exception:
        print(json.dumps({'error': 'DOCKER_INVENTORY_UNAVAILABLE', 'mode': 'READ_ONLY'}))
        return 1
    for container_id in ids:
        try:
            item = json.loads(command(['docker', 'inspect', '--format', INSPECT, container_id]))
            if not str(item.get('name', '')).lstrip('/').startswith('marina-'):
                continue
            if item['status'] == 'running' and item.get('service') == 'api':
                try:
                    item['api_runtime'] = json.loads(command(['docker', 'exec', '-i', container_id, 'python', '-'], input_text=API_PROBE))
                except Exception:
                    item['api_runtime'] = {'error': 'API_READ_UNAVAILABLE'}
            if item['status'] == 'running' and item.get('service') == 'postgres':
                try:
                    item['database'] = json.loads(command(['docker', 'exec', '-i', container_id, 'sh', '-c', PSQL], input_text=DB_PROBE))
                except Exception:
                    item['database'] = {'error': 'DB_READ_UNAVAILABLE'}
            report['containers'].append(item)
        except Exception:
            report['containers'].append({'id': container_id, 'error': 'CONTAINER_READ_UNAVAILABLE'})
    for folder in ('marina-smart-public-demo', 'marina-smart-demo'):
        path = Path.home() / folder
        if not path.is_dir():
            report['checkouts'].append({'directory': str(path), 'present': False})
            continue
        item = {'directory': str(path), 'present': True}
        try:
            item['source_commit'] = command(['git', '-C', str(path), 'rev-parse', 'HEAD'])
        except Exception:
            item['source_commit'] = 'unavailable'
        # Only report presence. Never open credentials or private overlay files.
        item['overlay_present'] = {name: (path / name).is_file() for name in
            ('.marina-demo-tunnel.yaml', '.marina-demo-assistant.yaml', '.marina-hotel01-green.yaml')}
        report['checkouts'].append(item)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
