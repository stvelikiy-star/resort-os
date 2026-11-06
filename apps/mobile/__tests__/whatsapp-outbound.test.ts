import { createLiveModules } from '../src/api/liveModules';
import { createHotelHttpClient } from '../src/api/http';
import { wasWhatsAppSendRejected } from '../src/lib/writeOutcome';
import { ApiError } from '../src/api/types';
import { acknowledgePendingOutbound, finishPendingOutbound, newOutboundKey, outboundJournalKey, readPendingOutbound, recordPendingOutbound, clearPendingOutbound } from '../src/lib/pendingOutbound';

const mockStore = new Map<string,string>();
jest.mock('../src/lib/storage', () => ({
  getDurableItem: async (key: string) => mockStore.get(key) ?? null,
  setDurableItem: async (key: string, value: string) => { mockStore.set(key,value); },
  removeDurableItem: async (key: string) => { mockStore.delete(key); },
}));
const response=(value: unknown,status=200)=>({ok:status>=200&&status<300,status,redirected:false,json:async()=>value} as Response);
const id='11111111-2222-3333-4444-555555555555';
const ack={conversation_id:id,message_id:'22222222-3333-4444-5555-666666666666',delivery_status:'QUEUED',idempotent_replay:false,counts_as_response:false,auto_sent:false};
beforeEach(()=>{mockStore.clear();jest.clearAllMocks();});
describe('RC8 WhatsApp outbound: explicit human send, never simulated delivery',()=>{
  it('uses the canonical send-text path, exact hotel cookie, and Idempotency-Key',async()=>{
    const transport=jest.fn(async()=>response(ack));
    const api=createLiveModules('https://hotel.example/core',transport as typeof fetch,'shared_auth_preview');
    const result=await api.sendWhatsAppText(id,'Hello','mobile-1111222233334444');
    expect(result.delivery_status).toBe('QUEUED');
    expect(result.counts_as_response).toBe(false);
    expect(transport).toHaveBeenCalledTimes(1);
    const [url,options]=transport.mock.calls[0] as unknown as [string,RequestInit];
    expect(url).toBe('https://hotel.example/core/api/v1/admin/inbox/conversations/'+id+'/send-text');
    expect(options).toMatchObject({method:'POST',credentials:'include',redirect:'error'});
    expect((options.headers as Record<string,string>)['Idempotency-Key']).toBe('mobile-1111222233334444');
    expect(JSON.parse(String(options.body))).toEqual({text:'Hello'});
  });
  it('retains durable journal on RC8 409 reconciliation requirement and never resends',async()=>{
    const transport=jest.fn(async()=>response({detail:{code:'OUTBOX_RECONCILIATION_REQUIRED',automatic_retry_safe:false}},409));
    const api=createLiveModules('https://hotel.example',transport as typeof fetch);
    const journal=outboundJournalKey('HOTEL_A','staff',id);
    const key='mobile-1111222233334444';
    expect(await recordPendingOutbound(journal,'Hello',key)).toBe(true);
    try {
      await api.sendWhatsAppText(id,'Hello',key);
      throw Error('Expected server rejection');
    } catch(error:unknown) {
      expect(error).toMatchObject({code:'CONFLICT'});
      // Match the screen's send-result policy: unknown 409 must stay pending.
      if (wasWhatsAppSendRejected(error)) await clearPendingOutbound(journal);
    } finally {
      finishPendingOutbound(journal);
    }
    expect((await readPendingOutbound(journal))?.key).toBe(key);
    expect(await recordPendingOutbound(journal,'Hello',newOutboundKey())).toBe(false);
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('only clears pending send for definitive pre-provider rejections',()=>{
    expect(wasWhatsAppSendRejected(new ApiError('CONFLICT'))).toBe(false);
    expect(wasWhatsAppSendRejected(new ApiError('OFFLINE'))).toBe(false);
    expect(wasWhatsAppSendRejected(new ApiError('UNKNOWN'))).toBe(false);
    expect(wasWhatsAppSendRejected(new ApiError('FORBIDDEN'))).toBe(false); // could be redirect refusal
    expect(wasWhatsAppSendRejected(new ApiError('BAD_REQUEST'))).toBe(true);
    expect(wasWhatsAppSendRejected(new ApiError('UNAUTHORIZED'))).toBe(true);
    expect(wasWhatsAppSendRejected(new ApiError('NOT_FOUND'))).toBe(true);
  });
  it('never retries a failed WhatsApp POST, even when the result is unknown',async()=>{
    const transport=jest.fn(async()=>{throw Error('lost ack');});
    const api=createLiveModules('https://hotel.example',transport as typeof fetch);
    await expect(api.sendWhatsAppText(id,'Hello','mobile-1111222233334444')).rejects.toMatchObject({code:'OFFLINE'});
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('refuses invented delivery status and malformed acknowledgement',async()=>{
    const transport=jest.fn(async()=>response({...ack,delivery_status:'DELIVERED_FAKE'}));
    const api=createLiveModules('https://hotel.example',transport as typeof fetch);
    await expect(api.sendWhatsAppText(id,'Hello','mobile-1111222233334444')).rejects.toMatchObject({code:'UNKNOWN'});
  });
  it('server 403/503 still block dispatch, never fall back to another sender',async()=>{
    for(const status of [403,503]){
      const transport=jest.fn(async()=>response({detail:'blocked'},status));
      const api=createLiveModules('https://hotel.example',transport as typeof fetch);
      await expect(api.sendWhatsAppText(id,'Hello','mobile-1111222233334444')).rejects.toMatchObject({code:status===403?'FORBIDDEN':'UNKNOWN'});
      expect(transport).toHaveBeenCalledTimes(1);
    }
  });
  it('requires validated idempotency keys and rejects dangerous route IDs before network',async()=>{
    const transport=jest.fn(async()=>response(ack));
    const api=createLiveModules('https://hotel.example',transport as typeof fetch);
    await expect(api.sendWhatsAppText(id,'Hello','bad')).rejects.toMatchObject({code:'BAD_REQUEST'});
    await expect(api.sendWhatsAppText('../bad','Hello','mobile-1111222233334444')).rejects.toMatchObject({code:'BAD_REQUEST'});
    expect(transport).not.toHaveBeenCalled();
    const primitive=createHotelHttpClient('https://hotel.example',transport as typeof fetch);
    await expect(primitive.request('GET','/api/v1/auth/me',undefined,'mobile-1111222233334444')).rejects.toMatchObject({code:'BAD_REQUEST'});
  });
  it('rejects an unconfigured capability and accepts explicitly configured RC8',async()=>{
    const transport=jest.fn().mockResolvedValueOnce(response({whatsapp:{configured:false,human_only:true,queued_only:true,max_text_length:4096}}))
      .mockResolvedValueOnce(response({whatsapp:{configured:true,human_only:true,queued_only:true,max_text_length:4096}}));
    const api=createLiveModules('https://hotel.example',transport as typeof fetch,'shared_auth_preview');
    expect((await api.outboundCapabilities()).whatsapp.configured).toBe(false);
    expect((await api.outboundCapabilities()).whatsapp.configured).toBe(true);
  });
});
describe('durable unresolved outbound journal',()=>{
  it('prevents duplicate attempts until an explicit reconciliation and survives remount',async()=>{
    const journal=outboundJournalKey('HOTEL_A','staff','conversation');
    const key=newOutboundKey();
    expect(key.length).toBeGreaterThanOrEqual(8);
    expect(await recordPendingOutbound(journal,'Hello',key)).toBe(true);
    expect(await recordPendingOutbound(journal,'Hello again',newOutboundKey())).toBe(false);
    finishPendingOutbound(journal);
    const pending=await readPendingOutbound(journal);
    expect(pending?.text).toBe('Hello');
    expect(await recordPendingOutbound(journal,'Hello again',newOutboundKey())).toBe(false);
    expect(await acknowledgePendingOutbound(journal,pending!)).toBe(true);
    expect(await readPendingOutbound(journal)).toBeNull();
    expect(await recordPendingOutbound(journal,'New intentional message',newOutboundKey())).toBe(true);
    await clearPendingOutbound(journal);
    finishPendingOutbound(journal);
  });
  it('isolates unresolved intents by property and employee',async()=>{
    const a=outboundJournalKey('A','one','c');
    const b=outboundJournalKey('B','one','c');
    const c=outboundJournalKey('A','two','c');
    await recordPendingOutbound(a,'A',newOutboundKey());
    finishPendingOutbound(a);
    expect(await readPendingOutbound(b)).toBeNull();
    expect(await readPendingOutbound(c)).toBeNull();
    expect((await readPendingOutbound(a))?.text).toBe('A');
  });
});
