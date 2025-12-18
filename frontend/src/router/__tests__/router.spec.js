import router from '@/router';
import axios from 'axios';

jest.mock('axios');

describe('router guards', () => {
  let consoleWarnSpy;

  beforeEach(() => {
    axios.get.mockReset();
    // 테스트 중 console.warn 출력 억제
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    // console.warn restore
    consoleWarnSpy?.mockRestore();
  });

  it('allows navigation when authenticated', async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: true } });
    await router.push('/result');
    expect(router.currentRoute.value.path).toBe('/result');
  });

  it('redirects to login when unauthenticated', async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    await router.push('/problems');
    expect(router.currentRoute.value.path).toBe('/login');
  });
});

