import { createHotelHttpClient } from '../src/api/http';
import { bindVerifiedHost } from '../src/api/unauthorizedSession';

const origin = 'https://platform.example/core';
const resp = (status: number) => ({
  status, ok: status >= 200 && status < 300, redirected: false,
  json: async () => ({ detail: 'SENSITIVE_SERVER_TEXT' }),
}) as Response;

describe('central 401 revocation for verified hotel data requests', () => {
  it('revokes the currently bound tenant on protected 401 exactly once, without retry', async () => {
    const revoked = jest.fn();
    const clear = bindVerifiedHost(origin, revoked);
    try {
      const transport = jest.fn(async () => resp(401));
      const http = createHotelHttpClient(origin, transport as unknown as typeof fetch);
      await expect(http.request('GET', '/api/v1/ops/tasks')).rejects.toMatchObject({ code: 'UNAUTHORIZED' });
      expect(transport).toHaveBeenCalledTimes(1);
      expect(revoked).toHaveBeenCalledTimes(1);
    } finally { clear(); }
  });

  it('ignores a delayed A 401 after a verified B login on the SAME HTTPS host', async () => {
    const revokedA = jest.fn(), revokedB = jest.fn();
    const clearA = bindVerifiedHost(origin, revokedA);
    const gate = { finish: (_: Response) => {} };
    const transport = jest.fn(() => new Promise<Response>(resolve => { gate.finish = resolve; }));
    const http = createHotelHttpClient(origin, transport as unknown as typeof fetch);
    const pending = http.request('GET', '/api/v1/admin/dashboard');
    // A has already left. Its stale HTTP request cannot revoke the new B.
    const clearB = bindVerifiedHost('https://platform.example', revokedB);
    try {
      gate.finish(resp(401));
      await expect(pending).rejects.toMatchObject({ code: 'UNAUTHORIZED' });
      expect(revokedA).not.toHaveBeenCalled();
      expect(revokedB).not.toHaveBeenCalled();
      // A request initiated under the newly verified B must revoke B.
      const next = createHotelHttpClient(origin, jest.fn(async () => resp(401)) as unknown as typeof fetch);
      await expect(next.request('GET','/api/v1/ops/tasks')).rejects.toMatchObject({ code: 'UNAUTHORIZED' });
      expect(revokedB).toHaveBeenCalledTimes(1);
    } finally { clearA(); clearB(); }
  });

  it.each([200, 503])('discards a delayed A response (%i) without retrying under B', async status => {
    const clearA = bindVerifiedHost(origin, jest.fn());
    let finish!: (response: Response) => void;
    const transport = jest.fn(() => new Promise<Response>(resolve => { finish = resolve; }));
    const http = createHotelHttpClient(origin, transport as unknown as typeof fetch);
    const pending = http.request('GET', '/api/v1/ops/tasks');
    const clearB = bindVerifiedHost(origin, jest.fn());
    try {
      const response = resp(status);
      const readBody = jest.spyOn(response, 'json');
      finish(response);
      await expect(pending).rejects.toMatchObject({ code: 'STALE_SESSION' });
      expect(readBody).not.toHaveBeenCalled();
      expect(transport).toHaveBeenCalledTimes(1);
    } finally { clearA(); clearB(); }
  });

  it('discards an A body if the session changes while reading it', async () => {
    const clearA = bindVerifiedHost(origin, jest.fn());
    let finish!: (value: unknown) => void;
    let reading!: () => void;
    const bodyStarted = new Promise<void>(resolve => { reading = resolve; });
    const json = () => new Promise<unknown>(resolve => { finish = resolve; reading(); });
    const transport = jest.fn(async () => ({ ...resp(200), json }) as Response);
    const http = createHotelHttpClient(origin, transport as unknown as typeof fetch);
    const pending = http.request('GET', '/api/v1/ops/tasks');
    await bodyStarted;
    const clearB = bindVerifiedHost(origin, jest.fn());
    try {
      finish({ hotel: 'A' });
      await expect(pending).rejects.toMatchObject({ code: 'STALE_SESSION' });
      expect(transport).toHaveBeenCalledTimes(1);
    } finally { clearA(); clearB(); }
  });

  it('does not sign out an existing employee after a rejected login, mode probe or 403', async () => {
    const revoked = jest.fn(), clear = bindVerifiedHost(origin, revoked);
    try {
      const http = createHotelHttpClient(origin, jest.fn(async () => resp(401)) as unknown as typeof fetch);
      await expect(http.request('POST', '/api/v1/auth/login', {username:'wrong'})).rejects.toMatchObject({code:'UNAUTHORIZED'});
      await expect(http.request('GET', '/api/v1/auth/mode')).rejects.toMatchObject({code:'UNAUTHORIZED'});
      const forbidden = createHotelHttpClient(origin, jest.fn(async () => resp(403)) as unknown as typeof fetch);
      await expect(forbidden.request('GET', '/api/v1/admin/dashboard')).rejects.toMatchObject({code:'FORBIDDEN'});
      expect(revoked).not.toHaveBeenCalled();
    } finally { clear(); }
  });

  it('does not revoke on server 503 or re-submit a lost financial write', async () => {
    const revoked=jest.fn(), clear=bindVerifiedHost(origin,revoked);
    try {
      const transport=jest.fn(async () => resp(503));
      const http=createHotelHttpClient(origin,transport as unknown as typeof fetch);
      await expect(http.request('POST','/api/v1/admin/pms/reservations/new/commit',{})).rejects.toMatchObject({code:'UNKNOWN'});
      expect(transport).toHaveBeenCalledTimes(1);
      expect(revoked).not.toHaveBeenCalled();
    } finally { clear(); }
  });
});
