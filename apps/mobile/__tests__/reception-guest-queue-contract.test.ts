import { createLiveModules } from '../src/api/liveModules';

const origin = 'https://reception.example.com/core';
const id = 'task-1';
const userId = 'reception-1';
const item = {
  id, title: 'Reception', status: 'OPEN', description: 'Guest request',
  room_code: '101', service_date: null, service_time: null, assigned_to_id: null,
};

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response;
}

it('reads the active queue and verifies claim and completion acknowledgements', async () => {
  const fetcher = jest.fn()
    .mockResolvedValueOnce(response({ items: [item] }))
    .mockResolvedValueOnce(response({ id, status: 'IN_PROGRESS', assigned_to_id: userId }))
    .mockResolvedValueOnce(response({ id, status: 'DONE' }));
  const live = createLiveModules(origin, fetcher);
  await expect(live.receptionGuestRequests()).resolves.toEqual([item]);
  await expect(live.updateReceptionGuestRequest(id, 'claim', userId)).resolves.toBe('IN_PROGRESS');
  await expect(live.updateReceptionGuestRequest(id, 'complete', userId)).resolves.toBe('DONE');
  expect(fetcher.mock.calls.map(([url, init]) => [new URL(url).pathname, new URL(url).search, init.method])).toEqual([
    ['/core/api/v1/ops/guest-requests', '?status=ACTIVE&limit=200', 'GET'],
    ['/core/api/v1/ops/guest-requests/task-1/claim', '', 'POST'],
    ['/core/api/v1/ops/guest-requests/task-1/complete', '', 'POST'],
  ]);
});

it('rejects malformed queue records and acknowledgements for another assignee', async () => {
  const fetcher = jest.fn()
    .mockResolvedValueOnce(response({ items: [{ ...item, assigned_to_id: false }] }))
    .mockResolvedValueOnce(response({ id, status: 'IN_PROGRESS', assigned_to_id: 'someone-else' }));
  const live = createLiveModules(origin, fetcher);
  await expect(live.receptionGuestRequests()).rejects.toThrow(/guest request field/);
  await expect(live.updateReceptionGuestRequest(id, 'claim', userId)).rejects.toThrow(/acknowledgement/);
});

it('blocks shared preview and invalid IDs before contacting the API', async () => {
  const fetcher = jest.fn();
  const shared = createLiveModules(origin, fetcher, 'shared_auth_preview');
  await expect(shared.receptionGuestRequests()).rejects.toThrow(/unavailable/);
  await expect(createLiveModules(origin, fetcher).updateReceptionGuestRequest('../task', 'complete', userId))
    .rejects.toThrow(/record reference/);
  expect(fetcher).not.toHaveBeenCalled();
});

it('does not repeat a mutation after a lost response', async () => {
  const fetcher = jest.fn().mockRejectedValue(new Error('lost response'));
  await expect(createLiveModules(origin, fetcher).updateReceptionGuestRequest(id, 'complete', userId))
    .rejects.toThrow(/connection unavailable/);
  expect(fetcher).toHaveBeenCalledTimes(1);
});
