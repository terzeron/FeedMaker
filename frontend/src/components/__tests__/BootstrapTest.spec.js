import { mount } from '@vue/test-utils';
import BootstrapTest from '../BootstrapTest.vue';

const stubs = {
  BButton: { template: '<button><slot /></button>' },
  BAlert: { template: '<div><slot /></div>' },
  BCard: { template: '<div><slot /></div>' },
  BCardText: { template: '<div><slot /></div>' },
  BTable: { template: '<table><slot /></table>' },
  BProgress: { template: '<div><slot /></div>' }
};

describe('BootstrapTest.vue', () => {
  it('renders basic elements and table rows', () => {
    const wrapper = mount(BootstrapTest, { global: { stubs } });
    expect(wrapper.text()).toContain('버튼 테스트');
    expect(wrapper.text()).toContain('알림 테스트');
    expect(wrapper.text()).toContain('카드 테스트');
    expect(wrapper.text()).toContain('테이블 테스트');
  });
});

