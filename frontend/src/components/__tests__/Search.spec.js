import { mount } from '@vue/test-utils';
import Search from '../Search.vue';
import MyButton from '../MyButton.vue';
import axios from 'axios';

jest.mock('axios');
axios.isCancel = jest.fn(() => false);

const stubs = {
  'font-awesome-icon': true,
  BButton: { template: '<button><slot /></button>' },
  BContainer: { template: '<div><slot /></div>' },
  BRow: { template: '<div><slot /></div>' },
  BCol: { template: '<div><slot /></div>' },
  BInputGroup: { template: '<div><slot /></div>' },
  BFormInput: { template: '<input />' },
  BInputGroupText: { template: '<div><slot /></div>' },
  BCard: { template: '<div><slot /><slot name="header" /></div>' },
  BCardBody: { template: '<div><slot /></div>' },
  BSpinner: { template: '<span />' }
};

const flushPromises = () => new Promise(r => setTimeout(r));

describe('Search.vue', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    axios.isCancel = jest.fn(() => false);
  });

  it('performs per-site search and renders results', async () => {
    // 1st call: site names
    axios.get.mockResolvedValueOnce({
      data: { status: 'success', site_names: ['funbe', 'toonkor'] }
    });
    // 2nd call: funbe result
    axios.get.mockResolvedValueOnce({
      data: { status: 'success', search_result: '<div><a href="https://a">제목1</a></div>' }
    });
    // 3rd call: toonkor result
    axios.get.mockResolvedValueOnce({
      data: { status: 'success', search_result: '' }
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } }
    });

    await wrapper.setData({ searchKeyword: '드래곤' });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.siteResults.length).toBe(2);
    expect(wrapper.vm.siteResults[0].name).toBe('funbe');
    expect(wrapper.vm.siteResults[0].status).toBe('success');
    expect(wrapper.vm.siteResults[0].html).toContain('제목1');
    expect(wrapper.vm.siteResults[1].name).toBe('toonkor');
    expect(wrapper.vm.siteResults[1].status).toBe('success');
    expect(wrapper.vm.siteResults[1].html).toBe('');
  });

  it('handles per-site search error', async () => {
    // 1st call: site names
    axios.get.mockResolvedValueOnce({
      data: { status: 'success', site_names: ['funbe'] }
    });
    // 2nd call: funbe fails
    axios.get.mockRejectedValueOnce(new Error('network'));

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } }
    });

    await wrapper.setData({ searchKeyword: '키워드' });
    await wrapper.vm.search();
    await flushPromises();

    expect(wrapper.vm.siteResults.length).toBe(1);
    expect(wrapper.vm.siteResults[0].status).toBe('error');
    expect(wrapper.vm.siteResults[0].error).toBeTruthy();
  });

  it('aborts previous search when new search starts', async () => {
    const abortSpy = jest.fn();
    global.AbortController = jest.fn(() => ({
      signal: { aborted: false },
      abort: abortSpy,
    }));

    // First search: site names (will be aborted)
    let resolveFirst;
    axios.get.mockImplementationOnce(() =>
      new Promise((resolve) => { resolveFirst = resolve; })
    );
    // Second search: site names
    axios.get.mockResolvedValueOnce({
      data: { status: 'success', site_names: [] }
    });

    const wrapper = mount(Search, {
      global: { stubs, components: { MyButton } }
    });

    await wrapper.setData({ searchKeyword: '드래곤' });
    // Start first search (won't resolve)
    const p1 = wrapper.vm.search();

    // Start second search - should abort first
    await wrapper.setData({ searchKeyword: '무림' });
    await wrapper.vm.search();
    await flushPromises();

    expect(abortSpy).toHaveBeenCalledTimes(1);
  });
});
