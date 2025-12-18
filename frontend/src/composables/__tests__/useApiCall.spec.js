import { useApiCall } from '@/composables/useApiCall';
import axios from 'axios';

jest.mock('axios');

describe('composables/useApiCall', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    axios.mockReset?.();
    axios.get?.mockReset?.();
    // 테스트 중 console.error 출력 억제
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    // console.error restore
    consoleErrorSpy?.mockRestore();
  });

  it('calls GET and returns data', async () => {
    axios.mockResolvedValueOnce({ data: { ok: true } });
    const { get, loading, error } = useApiCall();
    const data = await get('/ping');
    expect(data).toEqual({ ok: true });
    expect(loading.value).toBe(false);
    expect(error.value).toBeNull();
  });

  it('throws on failure status and sets error', async () => {
    axios.mockResolvedValueOnce({ data: { status: 'failure', message: 'bad' } });
    const { get, error } = useApiCall();
    await expect(get('/fail')).rejects.toThrow('bad');
    expect(error.value).toBeTruthy();
  });

  it('supports post/put/delete wrappers', async () => {
    axios.mockResolvedValue({ data: { ok: true } });
    const { post, put, del } = useApiCall();
    await expect(post('/a', { x: 1 })).resolves.toEqual({ ok: true });
    await expect(put('/a', { x: 1 })).resolves.toEqual({ ok: true });
    await expect(del('/a')).resolves.toEqual({ ok: true });
  });
});
