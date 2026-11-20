import { createHotelHttpClient } from '../src/api/http';

describe('financially sensitive mutation edge cases', () => {
  it('does not auto retry a booking even if a gateway fails', async () => {
    const fetchStub = jest.fn(async () => ({ok:false,status:503,redirected:false} as Response));
    const api = createHotelHttpClient('https://hotel.example',fetchStub as unknown as typeof fetch);
    await expect(api.request('POST','/api/v1/admin/pms/reservations/new/commit',{ expected_total_kgs:1800 })).rejects.toThrow();
    expect(fetchStub).toHaveBeenCalledTimes(1);
  });
  it('does not silently repeat release of HOLD after lost acknowledgement', async () => {
    const fetchStub = jest.fn(async () => { throw new TypeError('lost acknowledgement'); });
    const api = createHotelHttpClient('https://hotel.example',fetchStub as unknown as typeof fetch);
    await expect(api.request('DELETE','/api/v1/admin/pms/holds/h1')).rejects.toMatchObject({code:'OFFLINE'});
    expect(fetchStub).toHaveBeenCalledTimes(1);
  });
});
