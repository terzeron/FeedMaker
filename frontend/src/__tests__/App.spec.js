import { mount } from '@vue/test-utils';
import App from '../App.vue';

describe('App.vue', () => {
  it('renders navbar and links', () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          'router-link': { template: '<a><slot /></a>' },
          'router-view': true,
          'font-awesome-icon': true
        }
      }
    });

    expect(wrapper.find('nav.navbar').exists()).toBe(true);
    const text = wrapper.text();
    expect(text).toContain('실행 결과');
    expect(text).toContain('문제점과 상태');
    expect(text).toContain('피드 관리');
    expect(text).toContain('사이트 검색');
  });
});

