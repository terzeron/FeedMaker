import { getApiUrlPath, getCommonHeaders, handleApiError } from '@/utils/api';

describe('utils/api', () => {
  const origEnv = { ...process.env };
  let consoleSpy;

  beforeEach(() => {
    consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    process.env = { ...origEnv };
    consoleSpy.mockRestore();
  });

  it('returns api url from env or default', () => {
    process.env.VUE_APP_API_URL = 'https://api.example.com';
    expect(getApiUrlPath()).toBe('https://api.example.com');

    delete process.env.VUE_APP_API_URL;
    expect(getApiUrlPath()).toBe('http://localhost:8000');
  });

  it('returns common headers', () => {
    expect(getCommonHeaders()).toEqual({ 'Content-Type': 'application/json' });
  });

  it('handleApiError logs details for response/request/message', () => {
    handleApiError({ response: { data: { a: 1 }, status: 400 } }, 'ctx');
    handleApiError({ request: {} }, 'ctx');
    handleApiError(new Error('boom'), 'ctx');
    expect(consoleSpy).toHaveBeenCalled();
  });
});

