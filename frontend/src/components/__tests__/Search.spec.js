import { mount } from '@vue/test-utils';
import Search from '../Search.vue';
import MyButton from '../MyButton.vue';
import axios from 'axios';

jest.mock('axios');

const stubs = {
  'font-awesome-icon': true,
  BButton: { template: '<button><slot /></button>' },
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
  BTd: { template: '<td><slot /></td>' }
};

const flushPromises = () => new Promise(r => setTimeout(r));

describe('Search.vue', () => {
  it('performs search and renders results', async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        status: 'success',
        search_result_list: [
          ['제목1', 'https://a'],
          { title: '제목2', url: 'https://b' }
        ]
      }
    });

    const wrapper = mount(Search, {
      global: {
        stubs,
        components: { MyButton }
      }
    });

    await wrapper.setData({ searchKeyword: '키워드' });
    await wrapper.vm.search();
    await flushPromises();

    // shows table and two rows
    expect(wrapper.vm.searchResultlist.length).toBe(2);
    expect(wrapper.text()).toContain('제목1');
    expect(wrapper.text()).toContain('제목2');
  });

  it('handles search error', async () => {
    axios.get.mockRejectedValueOnce(new Error('network'));

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } }
    });

    await wrapper.setData({ searchKeyword: '키워드' });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.searchError).toBeTruthy();
    expect(wrapper.vm.searchResultlist).toEqual([]);
  });
});
