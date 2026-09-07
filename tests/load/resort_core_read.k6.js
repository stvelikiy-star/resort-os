import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const baseUrl = (__ENV.LOAD_BASE_URL || '').replace(/\/$/, '');
const declaredEnv = (__ENV.LOAD_TEST_ENV || '').toLowerCase();
const ownerUsername = __ENV.LOAD_OWNER_USERNAME || '';
const ownerPassword = __ENV.LOAD_OWNER_PASSWORD || '';
const enableAuthGrid = (__ENV.LOAD_AUTH_GRID || 'false').toLowerCase() === 'true';

function failClosed(message) {
  throw new Error(`LOAD TEST BLOCKED: ${message}`);
}

if (!baseUrl) failClosed('LOAD_BASE_URL is required');
if (!['ci', 'test', 'staging'].includes(declaredEnv)) {
  failClosed('LOAD_TEST_ENV must be exactly ci, test, or staging');
}

const urlMatch = baseUrl.match(/^https?:\/\/([^/:]+)(?::\d+)?(?:\/|$)/i);
if (!urlMatch) failClosed('LOAD_BASE_URL must be a valid http(s) URL');
const hostname = urlMatch[1].toLowerCase();

const explicitlyBlockedHosts = new Set([
  '3korony.com',
  'www.3korony.com',
]);
if (explicitlyBlockedHosts.has(hostname)) {
  failClosed('public production hostname is explicitly blocked');
}

const isLoopback = ['127.0.0.1', 'localhost'].includes(hostname);
const stagingMarker = hostname.includes('staging') || hostname.includes('test') || hostname.endsWith('.invalid');
if (!isLoopback && !stagingMarker) {
  failClosed('non-loopback target must contain staging/test marker or use an .invalid host');
}

if (enableAuthGrid && (!ownerUsername || !ownerPassword)) {
  failClosed('LOAD_AUTH_GRID=true requires LOAD_OWNER_USERNAME and LOAD_OWNER_PASSWORD');
}

const httpFailures = new Rate('resort_http_failures');
const availabilityLatency = new Trend('availability_latency_ms', true);
const gridLatency = new Trend('grid_latency_ms', true);

export const options = {
  scenarios: {
    resort_read_pressure: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: __ENV.LOAD_STAGE_1 || '30s', target: Number(__ENV.LOAD_VUS_1 || 10) },
        { duration: __ENV.LOAD_STAGE_2 || '60s', target: Number(__ENV.LOAD_VUS_2 || 25) },
        { duration: __ENV.LOAD_STAGE_3 || '60s', target: Number(__ENV.LOAD_VUS_3 || 50) },
        { duration: __ENV.LOAD_STAGE_4 || '30s', target: 0 },
      ],
      gracefulRampDown: '15s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],
    resort_http_failures: ['rate<0.01'],
    availability_latency_ms: ['p(95)<1000'],
    grid_latency_ms: ['p(95)<1200'],
  },
};

export function setup() {
  const ready = http.get(`${baseUrl}/ready`, { timeout: '5s' });
  const ok = check(ready, {
    'setup readiness is 200': (r) => r.status === 200,
  });
  if (!ok) failClosed(`target readiness failed with HTTP ${ready.status}`);

  if (!enableAuthGrid) return { cookie: null };

  const login = http.post(
    `${baseUrl}/api/v1/auth/login`,
    JSON.stringify({ username: ownerUsername, password: ownerPassword }),
    { headers: { 'Content-Type': 'application/json' }, timeout: '5s' },
  );
  const loginOk = check(login, {
    'setup owner login is 200': (r) => r.status === 200,
  });
  if (!loginOk) failClosed(`owner login failed with HTTP ${login.status}`);

  return { cookie: login.headers['Set-Cookie'] || null };
}

export default function (data) {
  const now = new Date();
  const checkIn = now.toISOString().slice(0, 10);
  const out = new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000);
  const checkOut = out.toISOString().slice(0, 10);

  const ready = http.get(`${baseUrl}/ready`, { timeout: '5s' });
  const readyOk = check(ready, { 'ready=200': (r) => r.status === 200 });
  httpFailures.add(!readyOk);

  const availability = http.get(
    `${baseUrl}/api/v1/booking/check-availability?check_in=${checkIn}&check_out=${checkOut}&adults=2&children=0`,
    { timeout: '5s' },
  );
  availabilityLatency.add(availability.timings.duration);
  const availabilityOk = check(availability, {
    'availability=200': (r) => r.status === 200,
    'availability has results': (r) => {
      try {
        const body = r.json();
        return Array.isArray(body.results);
      } catch (_) {
        return false;
      }
    },
  });
  httpFailures.add(!availabilityOk);

  if (enableAuthGrid && data.cookie) {
    const gridEnd = new Date(now.getTime() + 5 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const grid = http.get(`${baseUrl}/api/v1/pms/grid?start=${checkIn}&end=${gridEnd}`, {
      headers: { Cookie: data.cookie },
      timeout: '5s',
    });
    gridLatency.add(grid.timings.duration);
    const gridOk = check(grid, {
      'grid=200': (r) => r.status === 200,
      'grid exposes rooms array': (r) => {
        try {
          const body = r.json();
          return Array.isArray(body.rooms) && body.rooms.length > 0;
        } catch (_) {
          return false;
        }
      },
    });
    httpFailures.add(!gridOk);
  }

  sleep(Number(__ENV.LOAD_SLEEP_SECONDS || 0.2));
}
