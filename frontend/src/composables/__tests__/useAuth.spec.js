import { useAuth } from '@/composables/useAuth';
import axios from 'axios';

jest.mock('axios');
jest.mock('vue-router', () => ({
  useRouter: () => ({ push: jest.fn() })
}));

describe('composables/useAuth', () => {
  beforeEach(() => {
    axios.get.mockReset();
    axios.post.mockReset();
  });

  it('checkAuth sets authorized state', async () => {
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: true, name: 'User' } });
    const { checkAuth, isAuthorized, userName } = useAuth();
    await expect(checkAuth()).resolves.toBe(true);
    expect(isAuthorized.value).toBe(true);
    expect(userName.value).toBe('User');
  });

  it('logout clears state and calls API', async () => {
    axios.post.mockResolvedValueOnce({});
    const { logout, isAuthorized, userName } = useAuth();
    await logout();
    expect(axios.post).toHaveBeenCalled();
    expect(isAuthorized.value).toBe(false);
    expect(userName.value).toBeNull();
  });
});

