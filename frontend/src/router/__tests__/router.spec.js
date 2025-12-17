import router from '@/router';
import axios from 'axios';

jest.mock('axios');

describe('router guards', () => {
  beforeEach(() => {
    axios.get.mockReset();
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

