import { mount } from '@vue/test-utils';
import FeedManagement from '../FeedManagement.vue';
import axios from 'axios';

jest.mock('axios');

const stubs = {
  MyButton: { template: '<button><slot /></button>' },
  'font-awesome-icon': true,
  BAlert: { template: '<div><slot /></div>' },
  BModal: { template: '<div><slot /></div>' },
  BContainer: { template: '<div><slot /></div>' },
  BRow: { template: '<div><slot /></div>' },
  BCol: { template: '<div><slot /></div>' },
  BInputGroup: { template: '<div><slot /></div>' },
  BFormInput: { template: '<input />' },
  BInputGroupText: { template: '<div><slot /></div>' },
  BTableSimple: { template: '<table><slot /></table>' },
  BThead: { template: '<thead><slot /></thead>' },
  BTbody: { template: '<tbody><slot /></tbody>' },
  BTr: { template: '<tr><slot /></tr>' },
  BTh: { template: '<th><slot /></th>' },
  BTd: { template: '<td><slot /></td>' },
  BProgress: { template: '<div><slot /></div>' },
  BProgressBar: { template: '<div><slot /></div>' }
};

const flushPromises = () => new Promise(r => setTimeout(r));

describe('FeedManagement.vue', () => {
  it('loads groups on mount', async () => {
    axios.get.mockResolvedValueOnce({ data: { status: 'success', groups: [
      { name: 'group1', num_feeds: 1 },
      { name: 'group2', num_feeds: 0 }
    ]}});

    const wrapper = mount(FeedManagement, { global: { stubs, mocks: { $route: { params: {} } } } });
    await flushPromises();

    expect(wrapper.vm.groups.length).toBe(2);
    expect(wrapper.text()).not.toContain('그룹 목록 없음');
  });
});
