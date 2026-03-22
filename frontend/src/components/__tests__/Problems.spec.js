import { mount } from "@vue/test-utils";
import Problems from "../Problems.vue";
import axios from "axios";

jest.mock("axios");

const stubs = {
  "router-link": { template: "<a><slot /></a>" },
  "font-awesome-icon": true,
  BContainer: { template: "<div><slot /></div>" },
  BRow: { template: "<div><slot /></div>" },
  BCol: { template: "<div><slot /></div>" },
  BCardHeader: { template: "<div><slot /></div>" },
  BCardBody: { template: "<div><slot /></div>" },
  BModal: { template: "<div><slot /></div>" },
};

const flushPromises = () => new Promise((r) => setTimeout(r));

describe("Problems.vue", () => {
  beforeEach(() => {
    axios.get.mockReset();
  });

  it("loads problem tables and computes sorted lists", async () => {
    // Prepare a queue of axios.get responses matching call order
    // status_info
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "A",
            feed_name: "a",
            public_html: "O",
            http_request: "O",
            update_date: "2024-10-10",
            upload_date: "2024-10-11",
            access_date: "2024-10-12",
            view_date: "2024-10-13",
          },
        ],
      },
    });
    // progress_info
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "B",
            current_index: 1,
            total_item_count: 2,
            unit_size_per_day: 1,
            progress_ratio: 50,
            due_date: "2024-10-15",
          },
        ],
      },
    });
    // public_feed_info
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "C",
            feed_name: "c",
            num_items: 10,
            size: 100,
            upload_date: "2024-10-10",
          },
        ],
      },
    });
    // html_info
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [
            { feed_dir_path: "g/c", file_path: "g/c/file.html", size: 10 },
          ],
          html_file_with_many_image_tag_map: [
            { feed_dir_path: "g/c", file_path: "g/c/f2.html", count: 30 },
          ],
          html_file_without_image_tag_map: [
            { feed_dir_path: "g/c", file_path: "g/c/f3.html" },
          ],
          html_file_image_not_found_map: [
            { feed_dir_path: "g/c", file_path: "g/c/f4.html" },
          ],
        },
      },
    });
    // element_info
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [{ element_name: "title", count: 3 }],
      },
    });
    // list_url_info
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          { feed_title: "A", count: 5, group_name: "g", feed_name: "a" },
        ],
      },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist.length).toBe(1);
    expect(wrapper.vm.sortedProgressInfolist.length).toBe(1);
    expect(wrapper.vm.sortedPublicFeedInfolist.length).toBe(1);
    expect(wrapper.vm.sortedHtmlFileSizelist.length).toBe(1);
    expect(wrapper.vm.sortedElementInfolist.length).toBe(1);
    expect(wrapper.vm.sortedListUrlInfolist.length).toBe(1);
  });

  it("toggles sort direction when clicking the same column header", async () => {
    // Mock all 6 API calls with minimal data
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "B",
            feed_name: "b",
            public_html: "O",
            http_request: "O",
            update_date: "2024-10-10",
            upload_date: "2024-10-11",
            access_date: "2024-10-12",
            view_date: "2024-10-13",
          },
          {
            feed_title: "A",
            feed_name: "a",
            public_html: "O",
            http_request: "O",
            update_date: "2024-10-09",
            upload_date: "2024-10-10",
            access_date: "2024-10-11",
            view_date: "2024-10-12",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    // Default sort: feed_title asc
    expect(wrapper.vm.statusInfoSortBy).toBe("feed_title");
    expect(wrapper.vm.statusInfoSortDesc).toBe(false);
    expect(wrapper.vm.sortedStatusInfolist[0].feed_title).toBe("A");

    // Click same column -> toggle to desc
    wrapper.vm.sortTable("statusInfo", "feed_title");
    expect(wrapper.vm.statusInfoSortDesc).toBe(true);
    expect(wrapper.vm.sortedStatusInfolist[0].feed_title).toBe("B");

    // Click same column again -> toggle back to asc
    wrapper.vm.sortTable("statusInfo", "feed_title");
    expect(wrapper.vm.statusInfoSortDesc).toBe(false);
  });

  it("changes sortBy when clicking a different column header", async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "A",
            feed_name: "b",
            public_html: "O",
            http_request: "O",
            update_date: "2024-10-10",
            upload_date: "2024-10-11",
            access_date: "2024-10-12",
            view_date: "2024-10-13",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    // Click a different column
    wrapper.vm.sortTable("statusInfo", "feed_name");
    expect(wrapper.vm.statusInfoSortBy).toBe("feed_name");
    expect(wrapper.vm.statusInfoSortDesc).toBe(false);
  });

  it("showStatusInfoDeleteButton returns true when feed_title is empty and public_html is O", async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "",
            feed_name: "x",
            public_html: "O",
            http_request: "",
            update_date: "",
            upload_date: "",
            access_date: "",
            view_date: "",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(
      wrapper.vm.showStatusInfoDeleteButton({
        item: { feed_title: "", public_html: "O" },
      }),
    ).toBe(true);
    expect(
      wrapper.vm.showStatusInfoDeleteButton({
        item: { feed_title: "Some", public_html: "O" },
      }),
    ).toBe(false);
    expect(
      wrapper.vm.showStatusInfoDeleteButton({
        item: { feed_title: "", public_html: "" },
      }),
    ).toBe(false);
  });

  it("handles empty data arrays", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist).toEqual([]);
    expect(wrapper.vm.sortedProgressInfolist).toEqual([]);
    expect(wrapper.vm.sortedPublicFeedInfolist).toEqual([]);
  });

  it("date fields get date-cell class in rendered HTML", async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "A",
            feed_name: "a",
            public_html: "O",
            http_request: "O",
            update_date: "2024-10-10",
            upload_date: "2024-10-11",
            access_date: "2024-10-12",
            view_date: "2024-10-13",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const dateCells = wrapper.findAll(".date-cell");
    expect(dateCells.length).toBeGreaterThanOrEqual(4);
  });

  it("sorts progressInfo table by clicking a column", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "B",
            current_index: 5,
            total_item_count: 10,
            unit_size_per_day: 2,
            progress_ratio: 50,
            due_date: "2024-10-15",
          },
          {
            feed_title: "A",
            current_index: 1,
            total_item_count: 20,
            unit_size_per_day: 1,
            progress_ratio: 80,
            due_date: "2024-11-01",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    // Default sort: progress_ratio desc
    expect(wrapper.vm.progressInfoSortBy).toBe("progress_ratio");
    expect(wrapper.vm.progressInfoSortDesc).toBe(true);
    expect(wrapper.vm.sortedProgressInfolist[0].feed_title).toBe("A");

    // Click feed_title column -> sort by feed_title asc
    wrapper.vm.sortTable("progressInfo", "feed_title");
    expect(wrapper.vm.progressInfoSortBy).toBe("feed_title");
    expect(wrapper.vm.progressInfoSortDesc).toBe(false);
    expect(wrapper.vm.sortedProgressInfolist[0].feed_title).toBe("A");

    // Toggle same column -> desc
    wrapper.vm.sortTable("progressInfo", "feed_title");
    expect(wrapper.vm.progressInfoSortDesc).toBe(true);
    expect(wrapper.vm.sortedProgressInfolist[0].feed_title).toBe("B");
  });

  it("sorts publicFeedInfo table by clicking a column", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "X",
            feed_name: "x",
            num_items: 2,
            file_size: 100,
            upload_date: "2020-01-01",
          },
          {
            feed_title: "Y",
            feed_name: "y",
            num_items: 25,
            file_size: 50000,
            upload_date: "2024-10-01",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    // publicFeedInfo should have items (filtered by size < 4*1024 or num_items)
    expect(wrapper.vm.sortedPublicFeedInfolist.length).toBeGreaterThanOrEqual(
      1,
    );

    // Sort by feed_title
    wrapper.vm.sortTable("publicFeedInfo", "feed_title");
    expect(wrapper.vm.publicFeedInfoSortBy).toBe("feed_title");
    expect(wrapper.vm.publicFeedInfoSortDesc).toBe(false);
  });

  it("sorts htmlFileSize table by clicking a column", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [
            {
              feed_dir_path: "g/c",
              file_path: "g/c/html/file1.html",
              size: 10,
            },
            {
              feed_dir_path: "g/d",
              file_path: "g/d/html/file2.html",
              size: 50,
            },
          ],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedHtmlFileSizelist.length).toBe(2);

    // Sort by feed_title
    wrapper.vm.sortTable("htmlFileSize", "feed_title");
    expect(wrapper.vm.htmlFileSizeSortBy).toBe("feed_title");
    expect(wrapper.vm.htmlFileSizeSortDesc).toBe(false);

    // Toggle same column
    wrapper.vm.sortTable("htmlFileSize", "feed_title");
    expect(wrapper.vm.htmlFileSizeSortDesc).toBe(true);
  });

  it("sorts elementInfo table by clicking a column", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          { element_name: "title", count: 3 },
          { element_name: "link", count: 10 },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedElementInfolist.length).toBe(2);

    // Sort by element_name
    wrapper.vm.sortTable("elementInfo", "element_name");
    expect(wrapper.vm.elementInfoSortBy).toBe("element_name");
    expect(wrapper.vm.elementInfoSortDesc).toBe(false);
  });

  it("sorts listUrlInfo table by clicking a column", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          { feed_title: "A", count: 5, group_name: "g", feed_name: "a" },
          { feed_title: "B", count: 2, group_name: "g", feed_name: "b" },
        ],
      },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedListUrlInfolist.length).toBe(2);

    // Sort by feed_title
    wrapper.vm.sortTable("listUrlInfo", "feed_title");
    expect(wrapper.vm.listUrlInfoSortBy).toBe("feed_title");
    expect(wrapper.vm.listUrlInfoSortDesc).toBe(false);
  });

  it("sorts htmlFileWithoutImageTag table", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [
            { feed_dir_path: "g/a", file_path: "g/a/html/f1.html" },
            { feed_dir_path: "g/b", file_path: "g/b/html/f2.html" },
          ],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedHtmlFileWithoutImageTaglist.length).toBe(2);
    wrapper.vm.sortTable("htmlFileWithoutImageTag", "file_name");
    expect(wrapper.vm.htmlFileWithoutImageTagSortBy).toBe("file_name");
  });

  it("sorts htmlFileWithManyImageTag table", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [
            { feed_dir_path: "g/a", file_path: "g/a/html/f1.html", count: 30 },
            { feed_dir_path: "g/b", file_path: "g/b/html/f2.html", count: 50 },
          ],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedHtmlFileWithManyImageTaglist.length).toBe(2);
    wrapper.vm.sortTable("htmlFileWithManyImageTag", "feed_title");
    expect(wrapper.vm.htmlFileWithManyImageTagSortBy).toBe("feed_title");
  });

  it("sorts htmlFileWithImageNotFound table", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [
            { feed_dir_path: "g/a", file_path: "g/a/html/f1.html" },
            { feed_dir_path: "g/b", file_path: "g/b/html/f2.html" },
          ],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedHtmlFileWithImageNotFoundlist.length).toBe(2);
    wrapper.vm.sortTable("htmlFileWithImageNotFound", "file_name");
    expect(wrapper.vm.htmlFileWithImageNotFoundSortBy).toBe("file_name");
  });

  it("statusInfoDeleteClicked opens confirm modal and removes item on confirm", async () => {
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "",
            feed_name: "orphan",
            public_html: true,
            http_request: false,
            feedmaker: false,
            update_date: "",
            upload_date: "",
            access_date: "",
            view_date: "",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const item = wrapper.vm.statusInfolist[0];
    wrapper.vm.statusInfoDeleteClicked({ item });
    expect(wrapper.vm.showConfirmModal).toBe(true);

    // Confirm the action
    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "success" } });
    wrapper.vm.handleConfirmOk();
    expect(wrapper.vm.statusInfolist.length).toBe(0);
  });

  it("handles API failure responses for each problem type", async () => {
    // All 6 API calls return failure
    axios.get.mockResolvedValueOnce({
      data: { status: "failure" },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "failure" },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "failure" },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "failure" },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "failure" },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "failure" },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist).toEqual([]);
    expect(wrapper.vm.sortedProgressInfolist).toEqual([]);
    expect(wrapper.vm.sortedPublicFeedInfolist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileSizelist).toEqual([]);
    expect(wrapper.vm.sortedElementInfolist).toEqual([]);
    expect(wrapper.vm.sortedListUrlInfolist).toEqual([]);
  });

  it("handles API errors (catch branches) for each problem type", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    axios.get.mockRejectedValueOnce(new Error("network"));
    axios.get.mockRejectedValueOnce(new Error("network"));
    axios.get.mockRejectedValueOnce(new Error("network"));
    axios.get.mockRejectedValueOnce(new Error("network"));
    axios.get.mockRejectedValueOnce(new Error("network"));
    axios.get.mockRejectedValueOnce(new Error("network"));

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist).toEqual([]);
    expect(wrapper.vm.sortedProgressInfolist).toEqual([]);
    expect(wrapper.vm.sortedPublicFeedInfolist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileSizelist).toEqual([]);
    expect(wrapper.vm.sortedElementInfolist).toEqual([]);
    expect(wrapper.vm.sortedListUrlInfolist).toEqual([]);
    console.error.mockRestore();
  });

  it("handles object results (non-array) by converting to array", async () => {
    // status_info returns object instead of array
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          0: {
            feed_title: "A",
            feed_name: "a",
            public_html: true,
            http_request: true,
            feedmaker: true,
            update_date: "2024-10-10",
            upload_date: "2024-10-11",
            access_date: "2024-10-12",
            view_date: "2024-10-13",
          },
        },
      },
    });
    // progress_info returns object
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          0: {
            feed_title: "B",
            current_index: 1,
            total_item_count: 2,
            unit_size_per_day: 1,
            progress_ratio: 50,
            due_date: "2024-10-15",
          },
        },
      },
    });
    // public_feed_info returns object
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          0: {
            feed_title: "C",
            feed_name: "c",
            num_items: 2,
            file_size: 100,
            upload_date: "2020-01-01",
          },
        },
      },
    });
    // html_info with object maps
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: {
            0: { feed_dir_path: "g/c", file_path: "g/c/html/f.html", size: 10 },
          },
          html_file_with_many_image_tag_map: {
            0: {
              feed_dir_path: "g/c",
              file_path: "g/c/html/f2.html",
              count: 30,
            },
          },
          html_file_without_image_tag_map: {
            0: { feed_dir_path: "g/c", file_path: "g/c/html/f3.html" },
          },
          html_file_image_not_found_map: {
            0: { feed_dir_path: "g/c", file_path: "g/c/html/f4.html" },
          },
        },
      },
    });
    // element_info returns object
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: { 0: { element_name: "title", count: 3 } },
      },
    });
    // list_url_info returns object
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          0: { feed_title: "A", count: 5, group_name: "g", feed_name: "a" },
        },
      },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist.length).toBe(1);
    expect(wrapper.vm.sortedProgressInfolist.length).toBe(1);
    expect(wrapper.vm.sortedPublicFeedInfolist.length).toBeGreaterThanOrEqual(
      1,
    );
    expect(wrapper.vm.sortedHtmlFileSizelist.length).toBe(1);
    expect(wrapper.vm.sortedElementInfolist.length).toBe(1);
    expect(wrapper.vm.sortedListUrlInfolist.length).toBe(1);
  });

  it("publicFeedInfo applies warning/danger classes based on thresholds", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "Tiny",
            feed_name: "tiny",
            num_items: 2,
            file_size: 500,
            upload_date: "2020-01-01",
          },
          {
            feed_title: "Small",
            feed_name: "small",
            num_items: 25,
            file_size: 2000,
            upload_date: "2024-10-01",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const tinyItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "tiny",
    );
    expect(tinyItem.sizeIsDanger).toBe(true);
    expect(tinyItem.numItemsIsWarning).toBe(true);

    const smallItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "small",
    );
    expect(smallItem.sizeIsWarning).toBe(true);
    expect(smallItem.numItemsIsDanger).toBe(true);
  });

  it("handles null/undefined sub-maps in html_info", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: null,
          html_file_with_many_image_tag_map: undefined,
          html_file_without_image_tag_map: null,
          html_file_image_not_found_map: undefined,
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedHtmlFileSizelist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileWithManyImageTaglist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileWithoutImageTaglist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileWithImageNotFoundlist).toEqual([]);
  });

  it("handles non-array non-object result (null) for status_info, progress_info, etc.", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: null },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: null },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: null },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: null },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: null },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist).toEqual([]);
    expect(wrapper.vm.sortedProgressInfolist).toEqual([]);
    expect(wrapper.vm.sortedPublicFeedInfolist).toEqual([]);
    expect(wrapper.vm.sortedElementInfolist).toEqual([]);
    expect(wrapper.vm.sortedListUrlInfolist).toEqual([]);
  });

  it("publicFeedInfoDeleteClicked opens confirm modal", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "X",
            feed_name: "x",
            num_items: 2,
            file_size: 100,
            upload_date: "2020-01-01",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const item = wrapper.vm.publicFeedInfolist[0];
    wrapper.vm.publicFeedInfoDeleteClicked({ item });
    expect(wrapper.vm.showConfirmModal).toBe(true);

    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "success" } });
    wrapper.vm.handleConfirmOk();
    expect(wrapper.vm.publicFeedInfolist.length).toBe(0);
  });

  it("htmlFileSizeDeleteClicked opens confirm modal and removes item", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [
            {
              feed_dir_path: "g/c",
              file_path: "g/c/html/file1.html",
              size: 10,
            },
          ],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const item = wrapper.vm.htmlFileSizelist[0];
    wrapper.vm.htmlFileSizeDeleteClicked({ item });
    expect(wrapper.vm.showConfirmModal).toBe(true);

    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "success" } });
    wrapper.vm.handleConfirmOk();
    expect(wrapper.vm.htmlFileSizelist.length).toBe(0);
  });

  it("imageWithoutImageTagDeleteClicked removes item on confirm", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [
            { feed_dir_path: "g/a", file_path: "g/a/html/f1.html" },
          ],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const item = wrapper.vm.htmlFileWithoutImageTaglist[0];
    wrapper.vm.imageWithoutImageTagDeleteClicked({ item });
    expect(wrapper.vm.showConfirmModal).toBe(true);

    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "success" } });
    wrapper.vm.handleConfirmOk();
    expect(wrapper.vm.htmlFileWithoutImageTaglist.length).toBe(0);
  });

  it("imageWithManyImageTagDeleteClicked removes item on confirm", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [
            { feed_dir_path: "g/a", file_path: "g/a/html/f1.html", count: 30 },
          ],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const item = wrapper.vm.htmlFileWithManyImageTaglist[0];
    wrapper.vm.imageWithManyImageTagDeleteClicked({ item });

    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "success" } });
    wrapper.vm.handleConfirmOk();
    expect(wrapper.vm.htmlFileWithManyImageTaglist.length).toBe(0);
  });

  it("imageNotFoundDeleteClicked removes item on confirm", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [
            { feed_dir_path: "g/a", file_path: "g/a/html/f1.html" },
          ],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const item = wrapper.vm.htmlFileWithImageNotFoundlist[0];
    wrapper.vm.imageNotFoundDeleteClicked({ item });

    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "success" } });
    wrapper.vm.handleConfirmOk();
    expect(wrapper.vm.htmlFileWithImageNotFoundlist.length).toBe(0);
  });

  it("publicFeedInfo sets uploadDateIsWarning for old upload dates", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "Old",
            feed_name: "old",
            num_items: 10,
            file_size: 10000,
            upload_date: "2020-01-01",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const oldItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "old",
    );
    expect(oldItem).toBeTruthy();
    expect(oldItem.uploadDateIsWarning).toBe(true);
  });

  it("publicFeedInfo uses feed_name as fallback when feed_title is missing", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "",
            feed_name: "no_title_feed",
            num_items: 2,
            file_size: 100,
            upload_date: "2020-01-01",
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const item = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "no_title_feed",
    );
    expect(item).toBeTruthy();
    expect(item.feed_title).toBe("no_title_feed");
  });

  it("htmlInfo uses feed_dir_path as fallback for feed_title when missing", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [
            {
              feed_dir_path: "mygroup/myfeed",
              file_path: "mygroup/myfeed/html/page.html",
              size: 10,
            },
          ],
          html_file_with_many_image_tag_map: [
            {
              feed_dir_path: "g2/f2",
              file_path: "g2/f2/html/page2.html",
              count: 30,
            },
          ],
          html_file_without_image_tag_map: [
            {
              feed_dir_path: "g3/f3",
              file_path: "g3/f3/html/page3.html",
            },
          ],
          html_file_image_not_found_map: [
            {
              feed_dir_path: "g4/f4",
              file_path: "g4/f4/html/page4.html",
            },
          ],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    // feed_title should be set from feed_dir_path split
    expect(wrapper.vm.htmlFileSizelist[0].feed_title).toBe("myfeed");
    expect(wrapper.vm.htmlFileSizelist[0].file_name).toBe("page.html");
    expect(wrapper.vm.htmlFileWithManyImageTaglist[0].feed_title).toBe("f2");
    expect(wrapper.vm.htmlFileWithManyImageTaglist[0].file_name).toBe(
      "page2.html",
    );
    expect(wrapper.vm.htmlFileWithoutImageTaglist[0].feed_title).toBe("f3");
    expect(wrapper.vm.htmlFileWithoutImageTaglist[0].file_name).toBe(
      "page3.html",
    );
    expect(wrapper.vm.htmlFileWithImageNotFoundlist[0].feed_title).toBe("f4");
    expect(wrapper.vm.htmlFileWithImageNotFoundlist[0].file_name).toBe(
      "page4.html",
    );
  });

  it("publicFeedInfo filters items by num_items > 20 condition", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "Normal",
            feed_name: "normal",
            num_items: 10,
            file_size: 50000,
            upload_date: new Date().toISOString(),
          },
          {
            feed_title: "TooMany",
            feed_name: "toomany",
            num_items: 25,
            file_size: 50000,
            upload_date: new Date().toISOString(),
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    // "Normal" (num_items=10, file_size=50000, recent date) should be filtered OUT
    // "TooMany" (num_items=25 > 20) should be included
    const tooManyItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "toomany",
    );
    expect(tooManyItem).toBeTruthy();
    expect(tooManyItem.numItemsIsDanger).toBe(true);
  });

  it("publicFeedInfo filter exercises each condition independently", async () => {
    const recentDate = new Date().toISOString().substring(0, 12);
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "SmallSize",
            feed_name: "smallsize",
            num_items: 10,
            file_size: 2000,
            upload_date: recentDate,
          },
          {
            feed_title: "FewItems",
            feed_name: "fewitems",
            num_items: 3,
            file_size: 50000,
            upload_date: recentDate,
          },
          {
            feed_title: "ManyItems",
            feed_name: "manyitems",
            num_items: 25,
            file_size: 50000,
            upload_date: recentDate,
          },
          {
            feed_title: "Excluded",
            feed_name: "excluded",
            num_items: 10,
            file_size: 50000,
            upload_date: recentDate,
          },
        ],
      },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    // "Excluded" should NOT appear (all conditions false)
    const excludedItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "excluded",
    );
    expect(excludedItem).toBeFalsy();

    // "SmallSize" appears because file_size < 4096
    const smallItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "smallsize",
    );
    expect(smallItem).toBeTruthy();
    expect(smallItem.sizeIsWarning).toBe(true);

    // "FewItems" appears because num_items < 5
    const fewItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "fewitems",
    );
    expect(fewItem).toBeTruthy();
    expect(fewItem.numItemsIsWarning).toBe(true);

    // "ManyItems" appears because num_items > 20
    const manyItem = wrapper.vm.publicFeedInfolist.find(
      (i) => i.feed_name === "manyitems",
    );
    expect(manyItem).toBeTruthy();
    expect(manyItem.numItemsIsDanger).toBe(true);
  });

  it("htmlInfo converts object sub-maps using Object.values", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: {
            item1: {
              feed_dir_path: "g/f",
              file_path: "g/f/html/a.html",
              size: 10,
              feed_title: "existing",
            },
          },
          html_file_with_many_image_tag_map: {
            item1: {
              feed_dir_path: "g2/f2",
              file_path: "g2/f2/html/b.html",
              count: 30,
              feed_title: "existing2",
            },
          },
          html_file_without_image_tag_map: {
            item1: {
              feed_dir_path: "g3/f3",
              file_path: "g3/f3/html/c.html",
              feed_title: "existing3",
            },
          },
          html_file_image_not_found_map: {
            item1: {
              feed_dir_path: "g4/f4",
              file_path: "g4/f4/html/d.html",
              feed_title: "existing4",
            },
          },
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.htmlFileSizelist.length).toBe(1);
    expect(wrapper.vm.htmlFileSizelist[0].feed_title).toBe("existing");
    expect(wrapper.vm.htmlFileSizelist[0].file_name).toBe("a.html");
    expect(wrapper.vm.htmlFileWithManyImageTaglist.length).toBe(1);
    expect(wrapper.vm.htmlFileWithManyImageTaglist[0].file_name).toBe("b.html");
    expect(wrapper.vm.htmlFileWithoutImageTaglist.length).toBe(1);
    expect(wrapper.vm.htmlFileWithImageNotFoundlist.length).toBe(1);
  });

  it("handles non-object non-array result values for all API responses", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: "string_value" },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: 42 },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: false },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: "not_valid",
          html_file_with_many_image_tag_map: 123,
          html_file_without_image_tag_map: false,
          html_file_image_not_found_map: "invalid",
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: "not_an_array" },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: 99 },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.sortedStatusInfolist).toEqual([]);
    expect(wrapper.vm.sortedProgressInfolist).toEqual([]);
    expect(wrapper.vm.sortedPublicFeedInfolist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileSizelist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileWithManyImageTaglist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileWithoutImageTaglist).toEqual([]);
    expect(wrapper.vm.sortedHtmlFileWithImageNotFoundlist).toEqual([]);
    expect(wrapper.vm.sortedElementInfolist).toEqual([]);
    expect(wrapper.vm.sortedListUrlInfolist).toEqual([]);
  });

  it("removePublicFeed handles failure response", async () => {
    // Setup minimal mount
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    jest.spyOn(window, "alert").mockImplementation(() => {});
    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "failure", message: "error" } });
    wrapper.vm.removePublicFeed("test_feed");
    await flushPromises();
    expect(window.alert).toHaveBeenCalledWith(
      expect.stringContaining("오류가 발생하였습니다"),
    );
    window.alert.mockRestore();
  });

  it("removePublicFeed handles network error", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    jest.spyOn(window, "alert").mockImplementation(() => {});
    axios.delete = jest.fn().mockRejectedValueOnce(new Error("network error"));
    wrapper.vm.removePublicFeed("test_feed");
    await flushPromises();
    expect(window.alert).toHaveBeenCalledWith(
      expect.stringContaining("오류가 발생하였습니다"),
    );
    window.alert.mockRestore();
  });

  it("renders all table rows and cells when data is loaded", async () => {
    // status_info with group_name/feed_name for router-link
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "A",
            feed_name: "a",
            group_name: "g1",
            public_html: true,
            http_request: true,
            feedmaker: true,
            update_date: "2024-10-10",
            upload_date: "2024-10-11",
            access_date: "2024-10-12",
            view_date: "2024-10-13",
          },
        ],
      },
    });
    // progress_info with group_name/feed_name
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "B",
            feed_name: "b",
            group_name: "g1",
            current_index: 1,
            total_item_count: 2,
            unit_size_per_day: 1,
            progress_ratio: 50,
            due_date: "2024-10-15",
          },
        ],
      },
    });
    // public_feed_info with all flag variants
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          {
            feed_title: "Tiny",
            feed_name: "tiny",
            group_name: "g1",
            num_items: 2,
            file_size: 500,
            upload_date: "2020-01-01",
          },
          {
            feed_title: "Small",
            feed_name: "small",
            group_name: "g1",
            num_items: 25,
            file_size: 2000,
            upload_date: "2024-10-01",
          },
        ],
      },
    });
    // html_info with data in all sub-maps
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [
            {
              feed_dir_path: "g1/c",
              file_path: "g1/c/html/f.html",
              size: 10,
              feed_title: "HtmlSize",
            },
          ],
          html_file_with_many_image_tag_map: [
            {
              feed_dir_path: "g1/d",
              file_path: "g1/d/html/f2.html",
              count: 30,
              feed_title: "ManyImg",
            },
          ],
          html_file_without_image_tag_map: [
            {
              feed_dir_path: "g1/e",
              file_path: "g1/e/html/f3.html",
              feed_title: "NoImg",
            },
          ],
          html_file_image_not_found_map: [
            {
              feed_dir_path: "g1/f",
              file_path: "g1/f/html/f4.html",
              feed_title: "ImgNotFound",
            },
          ],
        },
      },
    });
    // element_info
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [{ element_name: "title", count: 3 }],
      },
    });
    // list_url_info with group_name/feed_name
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: [
          { feed_title: "Url", count: 5, group_name: "g1", feed_name: "a" },
        ],
      },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    await wrapper.vm.$nextTick();
    const html = wrapper.html();

    // status_info table: router-link with group_name/feed_name
    expect(html).toContain("/management/g1/a");
    // status_info table: date-cell class for date fields
    expect(wrapper.findAll(".date-cell").length).toBeGreaterThanOrEqual(4);
    // status_info table: action column with delete button
    expect(wrapper.findAll("tr").length).toBeGreaterThan(6);

    // progress_info table: progress_ratio with %
    expect(html).toContain("50%");
    // progress_info table: router-link with group_name/feed_name
    expect(html).toContain("/management/g1/b");

    // public_feed_info: text-danger for sizeIsDanger (file_size=500 < 1024)
    const dangerSpans = wrapper.findAll(".text-danger");
    expect(dangerSpans.length).toBeGreaterThanOrEqual(1);
    // public_feed_info: text-warning for sizeIsWarning (file_size=2000)
    const warningSpans = wrapper.findAll(".text-warning");
    expect(warningSpans.length).toBeGreaterThanOrEqual(1);
    // public_feed_info: size_formatted displayed
    expect(html).toContain("500");
    // public_feed_info: action delete button
    expect(html).toContain("Tiny");
    expect(html).toContain("Small");

    // html file tables: feed_title links with management path
    expect(html).toContain("HtmlSize");
    expect(html).toContain("/management/g1/c");
    expect(html).toContain("ManyImg");
    expect(html).toContain("/management/g1/d");
    expect(html).toContain("NoImg");
    expect(html).toContain("/management/g1/e");
    expect(html).toContain("ImgNotFound");
    expect(html).toContain("/management/g1/f");

    // element_info table renders element_name and count
    expect(html).toContain("title");
    expect(html).toContain("3");

    // list_url_info table: router-link
    expect(html).toContain("Url");
    expect(html).toContain("/management/g1/a");

    // Verify footer renders admin email and version
    expect(html).toContain("dev");
  });

  it("handleConfirmCancel closes modal and clears action", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const action = jest.fn();
    wrapper.vm.openConfirmModal("Test?", action);
    expect(wrapper.vm.showConfirmModal).toBe(true);

    wrapper.vm.handleConfirmCancel();
    expect(wrapper.vm.showConfirmModal).toBe(false);
    expect(wrapper.vm.pendingAction).toBeNull();
    expect(action).not.toHaveBeenCalled();
  });

  it("formatFileSize returns correct formatted sizes", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    expect(wrapper.vm.formatFileSize(0)).toBe("0 B");
    expect(wrapper.vm.formatFileSize(500)).toContain("B");
    expect(wrapper.vm.formatFileSize(2048)).toContain("KB");
    expect(wrapper.vm.formatFileSize(5 * 1024 * 1024)).toContain("MB");
    expect(wrapper.vm.formatFileSize(2 * 1024 * 1024 * 1024)).toContain("GB");
  });

  it("getManagementLink returns link or empty string", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    const link = wrapper.vm.getManagementLink("Title", "g1", "f1");
    expect(link).toContain("/management/g1/f1");
    expect(link).toContain("Title");
    expect(wrapper.vm.getManagementLink("", "g1", "f1")).toBe("");
  });

  it("removeHtmlFile handles failure and error responses", async () => {
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: {
        status: "success",
        result: {
          html_file_size_map: [],
          html_file_with_many_image_tag_map: [],
          html_file_without_image_tag_map: [],
          html_file_image_not_found_map: [],
        },
      },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });
    axios.get.mockResolvedValueOnce({
      data: { status: "success", result: [] },
    });

    const wrapper = mount(Problems, { global: { stubs } });
    await flushPromises();

    jest.spyOn(window, "alert").mockImplementation(() => {});

    // Test failure response
    axios.delete = jest
      .fn()
      .mockResolvedValueOnce({ data: { status: "failure", message: "fail" } });
    wrapper.vm.removeHtmlFile("g/f/html/test.html");
    await flushPromises();
    expect(window.alert).toHaveBeenCalledWith(
      expect.stringContaining("오류가 발생하였습니다"),
    );

    // Test network error
    axios.delete = jest.fn().mockRejectedValueOnce(new Error("network"));
    wrapper.vm.removeHtmlFile("g/f/html/test.html");
    await flushPromises();
    expect(window.alert).toHaveBeenCalledWith(
      expect.stringContaining("오류가 발생하였습니다"),
    );

    window.alert.mockRestore();
  });
});
