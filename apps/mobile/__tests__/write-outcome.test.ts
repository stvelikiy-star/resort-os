import { ApiError } from '../src/api/types';
import { wasWriteRejected } from '../src/lib/writeOutcome';

describe('mutation delivery uncertainty', () => {
  it('only explicit client rejections are safe to retry after the user corrects the request', () => {
    for (const code of ['BAD_REQUEST','CONFLICT','UNAUTHORIZED','FORBIDDEN','RATE_LIMIT','NOT_FOUND'] as const) {
      expect(wasWriteRejected(new ApiError(code))).toBe(true);
    }
  });
  it('fails closed on network loss, timeout, server 5xx and malformed acknowledgments', () => {
    expect(wasWriteRejected(new ApiError('OFFLINE'))).toBe(false);
    expect(wasWriteRejected(new ApiError('UNKNOWN'))).toBe(false);
    expect(wasWriteRejected(new Error('connection reset'))).toBe(false);
    expect(wasWriteRejected(null)).toBe(false);
  });
});
