import { mount } from '@vue/test-utils';
import Login from '../Login.vue';
import axios from 'axios';

jest.mock('axios');

jest.mock('vue-router', () => ({
  useRouter: () => ({ push: jest.fn() })
}));

const FacebookAuthStub = {
  name: 'FacebookAuth',
  template: '<div></div>',
  emits: ['auth-initialized'],
  mounted() {
    this.$emit('auth-initialized');
  },
  methods: {
    login: () => Promise.resolve('token'),
    logout: () => Promise.resolve(),
    getProfile: () => Promise.resolve({ name: 'Tester', email: 't@example.com' }),
    isInitialized: () => true
  }
};

const stubs = {
  'font-awesome-icon': true,
  FacebookAuth: FacebookAuthStub
};

const flushPromises = () => new Promise(r => setTimeout(r));

describe('Login.vue', () => {
  beforeEach(() => {
    axios.get.mockReset();
    axios.post.mockReset();
  });

  it('logs in and redirects on success', async () => {
    // initial auth check: not authenticated
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: false } });
    // login API
    axios.post.mockResolvedValueOnce({ data: { status: 'success' } });

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    // click login button
    const btns = wrapper.findAll('button');
    expect(btns.length).toBeGreaterThan(0);
    await btns[0].trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalled();
    expect(wrapper.text()).toContain('님으로 로그인하였습니다.');
  });

  it('shows logout when already authenticated and logs out', async () => {
    // initial auth check: authenticated
    axios.get.mockResolvedValueOnce({ data: { is_authenticated: true, name: 'Tester' } });
    axios.post.mockResolvedValueOnce({}); // logout API

    const wrapper = mount(Login, { global: { stubs } });
    await flushPromises();

    const logoutButton = wrapper.findAll('button').find(b => b.text().includes('로그아웃'));
    expect(logoutButton).toBeTruthy();
    await logoutButton.trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalled();
    // After logout, login button should be visible again
    const loginButton = wrapper.findAll('button').find(b => b.text().includes('로그인'));
    expect(loginButton).toBeTruthy();
  });
});
