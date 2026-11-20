import { createLiveModules } from '../src/api/liveModules';
const reservation='11111111-2222-3333-4444-555555555555';
const room='22222222-3333-4444-5555-666666666666';
const version='2026-11-06T05:22:00.123456';
const segment={room_id:room,start:'2026-11-08',end:'2026-11-10'};
const preview={reservation:{version},can_commit:true,proposed_check_in:segment.start,proposed_check_out:segment.end,conflicts:[],pricing:{suggested_total_kgs:10000,delta_kgs:5000}};
const committed={ok:true,reservation_id:reservation,version:'2026-11-06T05:23:00.123456',check_in:segment.start,check_out:segment.end};
const response=(v:unknown,status=200)=>({ok:status>=200&&status<300,status,redirected:false,json:async()=>v} as Response);
describe('pinned one-room PMS date change',()=>{
  it('calls preview and commit with the verified optimistic version and one segment',async()=>{
    const transport=jest.fn().mockResolvedValueOnce(response(preview)).mockResolvedValueOnce(response(committed));
    const api=createLiveModules('https://hotel.example/core',transport as typeof fetch,'shared_auth_preview');
    const p=await api.schedulePreview(reservation,[segment]);expect(p.can_commit).toBe(true);
    const c=await api.scheduleCommit(reservation,[segment],p.reservation.version);
    expect(c.ok).toBe(true);expect(c.reservation_id).toBe(reservation);
    expect(transport).toHaveBeenCalledTimes(2);
    const [previewUrl,previewInit]=(transport as jest.Mock).mock.calls[0] as [string,RequestInit];
    const [commitUrl,commitInit]=(transport as jest.Mock).mock.calls[1] as [string,RequestInit];
    expect(previewUrl).toContain('/api/v1/admin/pms/reservations/'+reservation+'/schedule/preview');
    expect(commitUrl).toContain('/api/v1/admin/pms/reservations/'+reservation+'/schedule/commit');
    expect(JSON.parse(String(previewInit.body))).toEqual({segments:[segment]});
    expect(JSON.parse(String(commitInit.body))).toEqual({segments:[segment],expected_version:version});
    expect(commitInit.credentials).toBe('include');
  });
  it('refuses malformed dates and multi-room schedules before sending anything',async()=>{
    const transport=jest.fn(async()=>response(preview));
    const api=createLiveModules('https://hotel.example',transport as typeof fetch);
    await expect(api.schedulePreview(reservation,[{...segment,start:'invalid'}])).rejects.toMatchObject({code:'BAD_REQUEST'});
    await expect(api.schedulePreview(reservation,[segment,segment])).rejects.toMatchObject({code:'BAD_REQUEST'});
    await expect(api.scheduleCommit(reservation,[segment],'short')).rejects.toMatchObject({code:'BAD_REQUEST'});
    expect(transport).not.toHaveBeenCalled();
  });
  it('treats stale 409 as rejection and never repeats a mutating commit',async()=>{
    const transport=jest.fn(async()=>response({detail:{code:'STALE_RESERVATION'}},409));
    const api=createLiveModules('https://hotel.example',transport as typeof fetch);
    await expect(api.scheduleCommit(reservation,[segment],version)).rejects.toMatchObject({code:'CONFLICT'});
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('fails closed for server 403 and shared 503 without bypass',async()=>{
    for(const status of [403,503]){
      const transport=jest.fn(async()=>response({detail:'denied'},status));
      const api=createLiveModules('https://hotel.example',transport as typeof fetch,'shared_auth_preview');
      await expect(api.scheduleCommit(reservation,[segment],version)).rejects.toMatchObject({code:status===403?'FORBIDDEN':'UNKNOWN'});
      expect(transport).toHaveBeenCalledTimes(1);
    }
  });
  it('does not treat malformed successful server ACK as committed',async()=>{
    const transport=jest.fn(async()=>response({...committed,ok:false}));
    const api=createLiveModules('https://hotel.example',transport as typeof fetch);
    await expect(api.scheduleCommit(reservation,[segment],version)).rejects.toMatchObject({code:'UNKNOWN'});
    expect(transport).toHaveBeenCalledTimes(1);
  });
});
