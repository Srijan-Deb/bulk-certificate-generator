import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, getJob, request } from './api';

afterEach(() => vi.unstubAllGlobals());
describe('API client', () => {
  it('parses successful JSON responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({job_id:'abc',status:'PENDING'}), {status:200,headers:{'Content-Type':'application/json'}})));
    await expect(request<{job_id:string}>('/jobs/abc')).resolves.toEqual({job_id:'abc',status:'PENDING'});
  });
  it('surfaces API validation errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Invalid spreadsheet'}), {status:422,headers:{'Content-Type':'application/json'}})));
    await expect(getJob('bad-id')).rejects.toMatchObject({name:'ApiError',status:422,message:'Invalid spreadsheet'} satisfies Partial<ApiError>);
  });
  it('surfaces network failures with a useful message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')));
    await expect(request('/health')).rejects.toThrow('Cannot reach the API');
  });
  it('handles auth token storage correctly', async () => {
    const store: Record<string, string> = {};
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] || null,
      setItem: (k: string, v: string) => { store[k] = v; },
      removeItem: (k: string) => { delete store[k]; },
    });
    const { getStoredToken, setStoredToken, removeStoredToken } = await import('./api');
    setStoredToken('test-jwt-token');
    expect(getStoredToken()).toBe('test-jwt-token');
    removeStoredToken();
    expect(getStoredToken()).toBe('');
  });
});
