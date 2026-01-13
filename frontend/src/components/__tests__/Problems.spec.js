import { mount } from '@vue/test-utils';
import Problems from '../Problems.vue';
import axios from 'axios';

jest.mock('axios');

const stubs = {
  'router-link': { template: '<a><slot /></a>' },
  'font-awesome-icon': true,
  BContainer: { template: '<div><slot /></div>' },
  BRow: { template: '<div><slot /></div>' },
  BCol: { template: '<div><slot /></div>' },
  BCardHeader: { template: '<div><slot /></div>' },
  BCardBody: { template: '<div><slot /></div>' },
  BModal: { template: '<div><slot /></div>' }
};

const flushPromises = () => new Promise(r => setTimeout(r));

describe('Problems.vue', () => {
  beforeEach(() => {
    axios.get.mockReset();
  });

  it('loads problem tables and computes sorted lists', async () => {
    // Prepare a queue of axios.get responses matching call order
    // status_info
    axios.get.mockResolvedValueOnce({ data: { status: 'success', result: [
      { feed_title: 'A', feed_name: 'a', public_html: 'O', http_request: 'O', update_date: '2024-10-10', upload_date: '2024-10-11', access_date: '2024-10-12', view_date: '2024-10-13' }
    ]}});
    // progress_info
    axios.get.mockResolvedValueOnce({ data: { status: 'success', result: [
      { feed_title: 'B', current_index: 1, total_item_count: 2, unit_size_per_day: 1, progress_ratio: 50, due_date: '2024-10-15' }
    ]}});
    // public_feed_info
    axios.get.mockResolvedValueOnce({ data: { status: 'success', result: [
      { feed_title: 'C', feed_name: 'c', num_items: 10, size: 100, upload_date: '2024-10-10' }
    ]}});
    // html_info
    axios.get.mockResolvedValueOnce({ data: { status: 'success', result: {
      html_file_size_map: [{ feed_dir_path: 'g/c', file_path: 'g/c/file.html', size: 10 }],
      html_file_with_many_image_tag_map: [{ feed_dir_path: 'g/c', file_path: 'g/c/f2.html', count: 30 }],
      html_file_without_image_tag_map: [{ feed_dir_path: 'g/c', file_path: 'g/c/f3.html' }],
      html_file_image_not_found_map: [{ feed_dir_path: 'g/c', file_path: 'g/c/f4.html' }]
    }}});
    // element_info
    axios.get.mockResolvedValueOnce({ data: { status: 'success', result: [
      { element_name: 'title', count: 3 }
    ]}});
    // list_url_info
    axios.get.mockResolvedValueOnce({ data: { status: 'success', result: [
      { feed_title: 'A', count: 5, group_name: 'g', feed_name: 'a' }
    ]}});

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist.length).toBe(1);
    expect(wrapper.vm.sortedProgressInfolist.length).toBe(1);
    expect(wrapper.vm.sortedPublicFeedInfolist.length).toBe(1);
    expect(wrapper.vm.sortedHtmlFileSizelist.length).toBe(1);
    expect(wrapper.vm.sortedElementInfolist.length).toBe(1);
    expect(wrapper.vm.sortedListUrlInfolist.length).toBe(1);
  });
});
