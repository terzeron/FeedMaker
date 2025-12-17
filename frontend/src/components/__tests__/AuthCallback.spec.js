import { mount } from '@vue/test-utils';
import AuthCallback from '../AuthCallback.vue';

jest.mock('vue-router', () => ({
  useRoute: () => ({ query: { access_token: 'abc' } }),
  useRouter: () => ({ push: jest.fn() })
}));

describe('AuthCallback.vue', () => {
  it('mounts without error and shows message', async () => {
    const wrapper = mount(AuthCallback);
    expect(wrapper.text()).toContain('로그인 중');
  });
});
