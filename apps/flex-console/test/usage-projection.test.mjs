// Offline acceptance model for section 5 of the proposed FLEX/PMS contract.
// Deployment identity and property links are synthetic, pre-verified inputs.
import assert from 'node:assert/strict';
import test from 'node:test';

const links = new Map([
  ['qa-east/property-1', 'hotel-A'],
  ['qa-west/property-1', 'hotel-B'],
]);
const events = new Map([
  ['pms.grid.opened', ['qa.calendar', 'interaction']],
  ['reservation.created', ['qa.booking', 'operation']],
]);
const fields = ['capability_key', 'event_id', 'event_name', 'occurred_at', 'platform',
  'property_id', 'result', 'role_category', 'schema_version'];
const calendar = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Bishkek', year: 'numeric', month: '2-digit', day: '2-digit',
});

function periods(instant) {
  const date = new Date(instant);
  if (!Number.isFinite(date.valueOf()) || date.toISOString() !== instant)
    throw new Error('Expected canonical UTC fixture time');
  const parts = Object.fromEntries(calendar.formatToParts(date).map(p => [p.type, p.value]));
  const day = [parts.year, parts.month, parts.day].join('-');
  const monday = new Date(day + 'T00:00:00Z');
  monday.setUTCDate(monday.getUTCDate() - (monday.getUTCDay() + 6) % 7);
  return {day, week: monday.toISOString().slice(0, 10), month: day.slice(0, 7)};
}

function project(deliveries) {
  const receipts = new Map();
  const buckets = new Map();
  for (const [deployment, event] of deliveries) {
    const hotel = links.get(deployment + '/' + event.property_id);
    const definition = events.get(event.event_name);
    if (!hotel || !definition || definition[0] !== event.capability_key ||
        JSON.stringify(Object.keys(event).sort()) !== JSON.stringify(fields) ||
        event.schema_version !== 1 || event.role_category !== 'RECEPTION' ||
        !['web', 'mobile'].includes(event.platform) ||
        !['success', 'failure'].includes(event.result) ||
        !/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(event.event_id))
      throw new Error('Rejected fixture');
    const windows = periods(event.occurred_at);
    const key = JSON.stringify([deployment, event.event_id]);
    const body = JSON.stringify(fields.map(f => event[f]));
    if (receipts.has(key)) {
      if (receipts.get(key) !== body) throw new Error('Conflicting replay');
      continue;
    }
    receipts.set(key, body);
    for (const [period, start] of Object.entries(windows)) {
      const dimensions = {hotel, period, start, measure: definition[1], event: event.event_name,
        capability: event.capability_key, platform: event.platform, role: event.role_category, result: event.result};
      const bucket = JSON.stringify(dimensions);
      buckets.set(bucket, (buckets.get(bucket) ?? 0) + 1);
    }
  }
  return Array.from(buckets, ([bucket, count]) => ({...JSON.parse(bucket), count}));
}

const base = {schema_version: 1, event_id: '00000000-0000-4000-8000-000000000001',
  property_id: 'property-1', event_name: 'reservation.created', capability_key: 'qa.booking',
  occurred_at: '2026-11-30T18:00:00.000Z', platform: 'web', role_category: 'RECEPTION', result: 'success'};

test('same delivery twice counts once, while distinct verified deployments own separate counts', () => {
  const reordered = Object.fromEntries(Object.entries(base).reverse());
  const rows = project([['qa-east', base], ['qa-east', reordered], ['qa-west', base]]);
  assert.equal(rows.length, 6);
  for (const hotel of ['hotel-A', 'hotel-B']) {
    const daily = rows.filter(r => r.hotel === hotel && r.period === 'day');
    assert.equal(daily.length, 1);
    assert.equal(daily[0].count, 1);
    assert.equal(daily[0].start, '2026-12-01');
  }
});

test('Bishkek midnight, Monday and month boundaries', () => {
  assert.deepEqual(periods('2026-11-29T17:59:59.999Z'), {day:'2026-11-29', week:'2026-11-23', month:'2026-11'});
  assert.deepEqual(periods('2026-11-29T18:00:00.000Z'), {day:'2026-11-30', week:'2026-11-30', month:'2026-11'});
  assert.deepEqual(periods(base.occurred_at), {day:'2026-12-01', week:'2026-11-30', month:'2026-12'});
});

test('clicks, failed operations and successful operations have independent counters', () => {
  const deliveries = Array.from({length:10}, (_, i) => ['qa-east', {...base,
    event_id: base.event_id.slice(0, -2) + String(10 + i), event_name:'pms.grid.opened', capability_key:'qa.calendar'}]);
  deliveries.push(['qa-east', base], ['qa-east', {...base, event_id:base.event_id.replace(/1$/, '2'), result:'failure'}]);
  const daily = project(deliveries).filter(row => row.period === 'day');
  assert.deepEqual(daily.map(r => [r.measure, r.result, r.count]),
    [['interaction','success',10], ['operation','success',1], ['operation','failure',1]]);
});

test('conflicting replay, unknown mapping, extra fields and unsupported dimensions are rejected', () => {
  assert.throws(() => project([['qa-east', base], ['qa-east', {...base, platform:'mobile'}]]), /Conflicting replay/);
  assert.throws(() => project([['qa-unmapped', base]]), /Rejected fixture/);
  for (const change of [{property_id:'other'}, {guest_name:'fixture'}, {schema_version:2},
    {capability_key:'unknown'}, {event_name:'unknown'}, {role_category:'someone'}, {result:'other'},
    {platform:'other'}, {event_id:'invalid'}])
    assert.throws(() => project([['qa-east', {...base, ...change}]]), /Rejected fixture/);
});
