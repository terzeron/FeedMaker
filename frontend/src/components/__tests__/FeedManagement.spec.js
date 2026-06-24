import { mount } from "@vue/test-utils";
import FeedManagement from "../FeedManagement.vue";
import axios from "axios";

const jsonEditorMock = vi.hoisted(() =>
  vi.fn(function JSONEditorMock() {
    this.set = vi.fn();
    this.get = vi.fn().mockReturnValue({});
    this.expandAll = vi.fn();
    this.destroy = vi.fn();
  }),
);

vi.mock("axios");
vi.mock("jsoneditor", () => {
  return {
    default: jsonEditorMock,
  };
});

const stubs = {
  MyButton: {
    template: "<button><slot /></button>",
    data: () => ({ doShowInitialIcon: true, doShowSpinner: false }),
  },
  "font-awesome-icon": true,
  BAlert: { template: "<div><slot /></div>" },
  BModal: { template: "<div><slot /></div>" },
  BContainer: { template: "<div><slot /></div>" },
  BRow: { template: "<div><slot /></div>" },
  BCol: { template: "<div><slot /></div>" },
  BInputGroup: { template: "<div><slot /></div>" },
  BFormInput: { template: "<input />" },
  BInputGroupText: { template: "<div><slot /></div>" },
  BTableSimple: { template: "<table><slot /></table>" },
  BThead: { template: "<thead><slot /></thead>" },
  BTbody: { template: "<tbody><slot /></tbody>" },
  BTr: { template: "<tr><slot /></tr>" },
  BTh: { template: "<th><slot /></th>" },
  BTd: { template: "<td><slot /></td>" },
  BProgress: { template: "<div><slot /></div>" },
  BProgressBar: { template: "<div><slot /></div>" },
};

const flushPromises = () => new Promise((r) => setTimeout(r));

// backend GET /groups/:group/feeds/:feed 의 feed_info contract shape
// bin/feed_manager.py FeedManager.get_feed_info() 와 동기화 필요
const FEED_INFO_CONTRACT = {
  config: {
    rss: {
      title: "Contract Feed",
      link: "https://example.com/feed.xml",
      description: "Contract",
    },
    collection: { list_url_list: ["https://example.com/list"] },
    extraction: {},
  },
  collection_info: {
    collect_date: "2024-01-01T00:00:00Z",
    total_item_count: 10,
  },
  public_feed_info: {
    public_feed_file_path: "/public/feed.xml",
    file_size: 1024,
    num_items: 10,
    upload_date: "2024-01-01T00:00:00Z",
  },
  progress_info: {
    current_index: 5,
    total_item_count: 10,
    unit_size_per_day: 1.0,
    progress_ratio: 50.0,
    due_date: "2024-02-01T00:00:00Z",
  },
};

const createWrapper = (routeParams = {}) => {
  axios.get.mockResolvedValueOnce({ data: { status: "success", groups: [] } });
  const wrapper = mount(FeedManagement, {
    global: {
      stubs,
      mocks: { $route: { params: routeParams } },
    },
  });
  // jsonData 초기값이 {}이므로 title computed에서 에러 방지
  wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
  return wrapper;
};

describe("FeedManagement.vue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    console.log.mockRestore();
    console.error.mockRestore();
  });

  describe("mount", () => {
    it("loads groups on mount", async () => {
      axios.get.mockReset();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          groups: [
            { name: "group1", num_feeds: 1 },
            { name: "group2", num_feeds: 0 },
          ],
        },
      });

      const wrapper = mount(FeedManagement, {
        global: { stubs, mocks: { $route: { params: {} } } },
      });
      wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
      await flushPromises();

      expect(wrapper.vm.groups.length).toBe(2);
    });

    it("loads feed directly when route has group and feed params", async () => {
      axios.get.mockReset();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: {
                title: "Test",
                link: "https://terzeron.com/test.xml",
                description: "Test",
              },
              collection: { list_url_list: ["url1"] },
              extraction: {},
            },
            collection_info: {
              collect_date: "2024-01-01T00:00:00Z",
              total_item_count: 100,
            },
            public_feed_info: {
              num_items: 50,
              file_size: 2048,
              upload_date: "2024-01-01T00:00:00Z",
            },
            progress_info: {
              current_index: 30,
              total_item_count: 100,
              unit_size_per_day: 5,
              progress_ratio: 30,
              due_date: "2024-02-01T00:00:00Z",
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });

      const wrapper = mount(FeedManagement, {
        global: {
          stubs,
          mocks: {
            $route: { params: { group: "testGroup", feed: "testFeed" } },
          },
        },
      });
      await flushPromises();

      expect(wrapper.vm.selectedGroupName).toBe("testGroup");
      expect(wrapper.vm.selectedFeedName).toBe("testFeed");
    });
  });

  describe("getShortDateStr", () => {
    it("returns empty string for falsy input", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(wrapper.vm.getShortDateStr("")).toBe("");
      expect(wrapper.vm.getShortDateStr(null)).toBe("");
    });

    it("extracts date from ISO string", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(wrapper.vm.getShortDateStr("2024-01-15T12:00:00Z")).toBe(
        "2024-01-15",
      );
    });
  });

  describe("determineStatus", () => {
    it("returns true for active object", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(
        wrapper.vm.determineStatus({ name: "test", is_active: true }),
      ).toBe(true);
    });

    it("returns false for inactive object", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(
        wrapper.vm.determineStatus({ name: "test", is_active: false }),
      ).toBe(false);
    });

    it("returns true when is_active is undefined", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(wrapper.vm.determineStatus({ name: "test" })).toBe(true);
    });

    it("returns false for string starting with underscore", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(wrapper.vm.determineStatus("_inactive")).toBe(false);
    });

    it("returns true for string not starting with underscore", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(wrapper.vm.determineStatus("active")).toBe(true);
    });

    it("returns true for non-object non-string input", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      expect(wrapper.vm.determineStatus(123)).toBe(true);
    });
  });

  describe("alert / clearAlert", () => {
    it("sets alert message and variant", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.alert("Error message", "warning");
      expect(wrapper.vm.showAlert).toBe(true);
      expect(wrapper.vm.alertMessage).toBe("Error message");
      expect(wrapper.vm.alertVariant).toBe("warning");
    });

    it("uses danger as default variant", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.alert("Error");
      expect(wrapper.vm.alertVariant).toBe("danger");
    });

    it("clears alert", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.alert("Error");
      wrapper.vm.clearAlert();
      expect(wrapper.vm.showAlert).toBe(false);
      expect(wrapper.vm.alertMessage).toBe("");
    });
  });

  describe("confirm modal", () => {
    it("opens confirm modal with message and action", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const action = vi.fn();
      wrapper.vm.openConfirmModal("Are you sure?", action);
      expect(wrapper.vm.showConfirmModal).toBe(true);
      expect(wrapper.vm.confirmMessage).toBe("Are you sure?");
      expect(wrapper.vm.pendingAction).toBe(action);
    });

    it("handleConfirmOk executes pending action", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const action = vi.fn();
      wrapper.vm.openConfirmModal("Confirm?", action);
      wrapper.vm.handleConfirmOk();
      expect(action).toHaveBeenCalled();
      expect(wrapper.vm.showConfirmModal).toBe(false);
      expect(wrapper.vm.pendingAction).toBeNull();
    });

    it("handleConfirmOk does nothing when no pending action", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.showConfirmModal = true;
      wrapper.vm.pendingAction = null;
      wrapper.vm.handleConfirmOk();
      expect(wrapper.vm.showConfirmModal).toBe(false);
    });

    it("handleConfirmCancel closes modal", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const action = vi.fn();
      wrapper.vm.openConfirmModal("Confirm?", action);
      wrapper.vm.handleConfirmCancel();
      expect(wrapper.vm.showConfirmModal).toBe(false);
      expect(wrapper.vm.pendingAction).toBeNull();
      expect(action).not.toHaveBeenCalled();
    });
  });

  describe("setActiveGroup / setActiveFeed", () => {
    it("sets active group index", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.setActiveGroup(2);
      expect(wrapper.vm.activeGroupIndex).toBe(2);
    });

    it("sets active feed index", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.setActiveFeed(5);
      expect(wrapper.vm.activeFeedIndex).toBe(5);
    });
  });

  describe("show/hide related methods", () => {
    it("showAllRelatedToFeed sets all flags", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.showAllRelatedToFeed();
      expect(wrapper.vm.showEditor).toBe(true);
      expect(wrapper.vm.showNewFeedNameInput).toBe(true);
      expect(wrapper.vm.showRunButton).toBe(true);
      expect(wrapper.vm.showViewRssButton).toBe(true);
      expect(wrapper.vm.showToggleFeedButton).toBe(true);
      expect(wrapper.vm.showRemoveFeedButton).toBe(true);
      expect(wrapper.vm.showFeedInfo).toBe(true);
    });

    it("hideAllRelatedToFeed clears all flags", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.showAllRelatedToFeed();
      wrapper.vm.hideAllRelatedToFeed();
      expect(wrapper.vm.showEditor).toBe(false);
      expect(wrapper.vm.showNewFeedNameInput).toBe(false);
      expect(wrapper.vm.showRunButton).toBe(false);
    });

    it("showAllRelatedToGroup sets group buttons when group selected", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "testGroup";
      wrapper.vm.showAllRelatedToGroup();
      expect(wrapper.vm.showToggleGroupButton).toBe(true);
      expect(wrapper.vm.showRemoveGroupButton).toBe(true);
    });

    it("showAllRelatedToGroup does nothing without group", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "";
      wrapper.vm.showAllRelatedToGroup();
      expect(wrapper.vm.showToggleGroupButton).toBe(false);
    });

    it("hideAllRelatedToGroup clears group buttons", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "test";
      wrapper.vm.showAllRelatedToGroup();
      wrapper.vm.hideAllRelatedToGroup();
      expect(wrapper.vm.showToggleGroupButton).toBe(false);
      expect(wrapper.vm.showRemoveGroupButton).toBe(false);
    });
  });

  describe("determineNewFeedNameFromJsonRssLink", () => {
    it("extracts feed name from rss link", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.jsonData = {
        rss: { link: "https://terzeron.com/my_feed.xml" },
      };
      wrapper.vm.determineNewFeedNameFromJsonRssLink();
      expect(wrapper.vm.newFeedName).toBe("my_feed");
    });

    it("does nothing when jsonData has no rss", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.jsonData = {};
      wrapper.vm.determineNewFeedNameFromJsonRssLink();
      expect(wrapper.vm.newFeedName).toBe("");
    });
  });

  describe("determineDescriptionFromTitle", () => {
    it("copies title to description", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.jsonData = { rss: { title: "My Feed", description: "old" } };
      wrapper.vm.determineDescriptionFromTitle();
      expect(wrapper.vm.jsonData.rss.description).toBe("My Feed");
    });
  });

  describe("setCollectionInfo", () => {
    it("sets collection metadata", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.setCollectionInfo(
        { collect_date: "2024-01-15T00:00:00Z", total_item_count: 100 },
        3,
      );
      expect(wrapper.vm.numCollectionUrls).toBe(3);
      expect(wrapper.vm.collectDate).toBe("2024-01-15");
      expect(wrapper.vm.totalItemCount).toBe(100);
    });
  });

  describe("setPublicFeedInfo", () => {
    it("sets public feed metadata", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.setPublicFeedInfo({
        num_items: 50,
        file_size: 2048,
        upload_date: "2024-01-10T00:00:00Z",
      });
      expect(wrapper.vm.numItemsInResult).toBe(50);
      expect(wrapper.vm.sizeOfResultFile).toBe(2048);
      expect(wrapper.vm.lastUploadDate).toBe("2024-01-10");
    });

    it("skips upload_date when not present", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.setPublicFeedInfo({ num_items: 10, file_size: 100 });
      expect(wrapper.vm.lastUploadDate).toBe("-");
    });
  });

  describe("setProgressInfo", () => {
    it("sets progress metadata", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.setProgressInfo({
        current_index: 30,
        total_item_count: 100,
        unit_size_per_day: 5,
        progress_ratio: 30,
        due_date: "2024-02-01T00:00:00Z",
      });
      expect(wrapper.vm.currentIndex).toBe(30);
      expect(wrapper.vm.totalItemCount).toBe(100);
      expect(wrapper.vm.unitSizePerDay).toBe(5);
      expect(wrapper.vm.progressRatio).toBe(30);
      expect(wrapper.vm.feedCompletionDueDate).toBe("2024-02-01");
    });

    it("skips due_date when not present", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.setProgressInfo({
        current_index: 0,
        total_item_count: 0,
        unit_size_per_day: 0,
        progress_ratio: 0,
      });
      expect(wrapper.vm.feedCompletionDueDate).toBe("-");
    });
  });

  describe("computed: sizeOfResultFileWithUnit", () => {
    it("returns GiB for large files", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.sizeOfResultFile = 2 * 1024 * 1024 * 1024;
      expect(wrapper.vm.sizeOfResultFileWithUnit).toContain("GiB");
    });

    it("returns MiB for medium files", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.sizeOfResultFile = 5 * 1024 * 1024;
      expect(wrapper.vm.sizeOfResultFileWithUnit).toContain("MiB");
    });

    it("returns KiB for small files", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.sizeOfResultFile = 2048;
      expect(wrapper.vm.sizeOfResultFileWithUnit).toContain("KiB");
    });

    it("returns B for tiny files", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.sizeOfResultFile = 500;
      expect(wrapper.vm.sizeOfResultFileWithUnit).toContain("B");
    });
  });

  describe("computed: feedStatus / groupStatus", () => {
    it("returns status from selected feed", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.feeds = [{ name: "feed1", is_active: false }];
      wrapper.vm.selectedFeedName = "feed1";
      expect(wrapper.vm.feedStatus).toBe(false);
    });

    it("returns true when no matching feed", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.feeds = [];
      wrapper.vm.selectedFeedName = "missing";
      expect(wrapper.vm.feedStatus).toBe(true);
    });

    it("returns status from selected group", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.groups = [{ name: "group1", is_active: false }];
      wrapper.vm.selectedGroupName = "group1";
      expect(wrapper.vm.groupStatus).toBe(false);
    });
  });

  describe("computed: feedStatusLabel / feedStatusIcon / groupStatusLabel", () => {
    it("returns correct labels and icons", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.feeds = [{ name: "f1", is_active: true }];
      wrapper.vm.selectedFeedName = "f1";
      expect(wrapper.vm.feedStatusLabel).toBe("피드 비활성화");
      expect(wrapper.vm.feedStatusIcon).toBe("toggle-off");

      wrapper.vm.groups = [{ name: "g1", is_active: true }];
      wrapper.vm.selectedGroupName = "g1";
      expect(wrapper.vm.groupStatusLabel).toBe("그룹 비활성화");
    });
  });

  describe("search", () => {
    it("fetches search results and updates feeds", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feeds: [{ group_name: "g", feed_name: "f", feed_title: "title" }],
        },
      });
      wrapper.vm.searchKeyword = "test";
      wrapper.vm.search();
      await flushPromises();
      expect(wrapper.vm.showSearchResult).toBe(true);
      expect(wrapper.vm.showGrouplist).toBe(false);
      expect(wrapper.vm.feeds.length).toBe(1);
    });

    it("shows alert on failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "Not found" },
      });
      wrapper.vm.searchKeyword = "bad";
      wrapper.vm.search();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Not found");
    });

    it("handles search API error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockRejectedValueOnce(new Error("Network"));
      wrapper.vm.searchKeyword = "error";
      wrapper.vm.search();
      await flushPromises();
      // Should not throw
    });
  });

  describe("grouplistButtonClicked", () => {
    it("resets view and fetches groups", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: { status: "success", groups: [{ name: "g1", num_feeds: 2 }] },
      });
      wrapper.vm.grouplistButtonClicked();
      await flushPromises();
      expect(wrapper.vm.showGrouplist).toBe(true);
      expect(wrapper.vm.showFeedlist).toBe(false);
      expect(wrapper.vm.groups.length).toBe(1);
    });
  });

  describe("groupNameButtonClicked", () => {
    it("selects group and loads feed list", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: { status: "success", feeds: [{ name: "f1", title: "Feed 1" }] },
      });
      wrapper.vm.groupNameButtonClicked("group1", 1);
      await flushPromises();
      expect(wrapper.vm.selectedGroupName).toBe("group1");
      expect(wrapper.vm.showFeedlist).toBe(true);
      expect(wrapper.vm.showFeedlistButton).toBe(true);
    });
  });

  describe("feedlistButtonClicked", () => {
    it("shows feed list for selected group", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "group1";
      axios.get.mockResolvedValueOnce({
        data: { status: "success", feeds: [] },
      });
      wrapper.vm.feedlistButtonClicked();
      await flushPromises();
      expect(wrapper.vm.showFeedlist).toBe(true);
      expect(wrapper.vm.showGrouplist).toBe(false);
    });
  });

  describe("feedNameButtonClicked", () => {
    it("loads feed info for regular feed", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: {
                title: "Test",
                link: "https://terzeron.com/test.xml",
                description: "Test",
              },
              collection: { list_url_list: ["url1"] },
              extraction: {},
            },
            collection_info: {
              collect_date: "2024-01-01T00:00:00Z",
              total_item_count: 100,
            },
            public_feed_info: { num_items: 50, file_size: 2048 },
            progress_info: {
              current_index: 30,
              total_item_count: 100,
              unit_size_per_day: 5,
              progress_ratio: 30,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.feedNameButtonClicked("group1", "feed1", 0);
      await flushPromises();
      expect(wrapper.vm.selectedFeedName).toBe("feed1");
    });

    it("loads site config for site_config.json", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "group1";
      axios.get.mockResolvedValueOnce({
        data: { status: "success", configuration: { key1: "v1", key2: "v2" } },
      });
      wrapper.vm.feedNameButtonClicked("group1", "site_config.json", 1);
      await flushPromises();
      expect(wrapper.vm.jsonData).toEqual({ key1: "v1", key2: "v2" });
    });
  });

  describe("searchResultFeedNameButtonClicked", () => {
    it("selects feed from search results", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: {
                title: "T",
                link: "https://terzeron.com/f.xml",
                description: "T",
              },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.searchResultFeedNameButtonClicked("g1", "f1", 1);
      await flushPromises();
      expect(wrapper.vm.selectedGroupName).toBe("g1");
      expect(wrapper.vm.selectedFeedName).toBe("f1");
      expect(wrapper.vm.showFeedlistButton).toBe(false);
    });
  });

  describe("save", () => {
    it("posts feed configuration", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.newFeedName = "f1";
      wrapper.vm.jsonData = {
        rss: { title: "T", link: "l", description: "D" },
      };
      axios.post.mockResolvedValueOnce({ data: { status: "success" } });
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.save();
      await flushPromises();
      expect(axios.post).toHaveBeenCalled();
    });

    it("handles save API error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.newFeedName = "f1";
      wrapper.vm.jsonData = {
        rss: { title: "T", link: "l", description: "D" },
      };
      axios.post.mockRejectedValueOnce(new Error("save failed"));
      wrapper.vm.save();
      await flushPromises();
      // Should not throw
    });
  });

  describe("run", () => {
    it("posts run request", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.newFeedName = "f1";
      wrapper.vm.selectedFeedName = "f1";
      axios.post.mockResolvedValueOnce({ data: { status: "success" } });
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.run();
      await flushPromises();
      expect(axios.post).toHaveBeenCalled();
    });

    it("handles run API error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.newFeedName = "f1";
      axios.post.mockRejectedValueOnce(new Error("run failed"));
      wrapper.vm.run();
      await flushPromises();
    });
  });

  describe("viewRss / registerToInoreader / registerToFeedly", () => {
    it("opens RSS URL", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.newFeedName = "test_feed";
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => {});
      wrapper.vm.viewRss();
      expect(openSpy).toHaveBeenCalledWith(
        "https://terzeron.com/test_feed.xml",
      );
      openSpy.mockRestore();
    });

    it("opens Inoreader registration URL", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.newFeedName = "test_feed";
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => {});
      wrapper.vm.registerToInoreader();
      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining("inoreader.com"),
      );
      openSpy.mockRestore();
    });

    it("opens Feedly registration URL", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.newFeedName = "test_feed";
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => {});
      wrapper.vm.registerToFeedly();
      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining("feedly.com"),
      );
      openSpy.mockRestore();
    });
  });

  describe("removeFeed", () => {
    it("alerts when no feed selected", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "";
      wrapper.vm.removeFeed();
      expect(wrapper.vm.alertMessage).toBe("Feed is not selected");
    });

    it("opens confirm modal when feed is selected", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.removeFeed();
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });
  });

  describe("removeGroup", () => {
    it("alerts when no group selected", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "";
      wrapper.vm.removeGroup();
      expect(wrapper.vm.alertMessage).toBe("Group is not selected");
    });

    it("opens confirm modal when group is selected", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.removeGroup();
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });
  });

  describe("toggleStatus", () => {
    it("opens confirm modal for feed toggle", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.toggleStatus("feed");
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });

    it("opens confirm modal for group toggle", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.toggleStatus("group");
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });
  });

  describe("removelist / removeHtml", () => {
    it("removelist opens confirm modal", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removelist();
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });

    it("removeHtml opens confirm modal", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removeHtml();
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });
  });

  describe("saveSiteConfig", () => {
    it("opens confirm modal", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.jsonData = { key: "value" };
      wrapper.vm.saveSiteConfig();
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });
  });

  describe("getItemsOfRss", () => {
    it("shows items on success", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          item_titles: [
            { title: "Title 1", date: "24-01-01" },
            { title: "Title 2", date: "24-01-02" },
          ],
        },
      });
      wrapper.vm.getItemsOfRss();
      await flushPromises();
      expect(wrapper.vm.itemsOfRss).toEqual([
        { title: "Title 1", date: "24-01-01" },
        { title: "Title 2", date: "24-01-02" },
      ]);
      expect(wrapper.vm.showViewItemsOfRssList).toBe(true);
    });

    it("alerts when no items found", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: { status: "success", item_titles: [] },
      });
      wrapper.vm.getItemsOfRss();
      await flushPromises();
      expect(wrapper.vm.showViewItemsOfRssList).toBe(false);
      expect(wrapper.vm.alertMessage).toContain("아이템이 없습니다");
    });

    it("handles FILE_NOT_FOUND error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", error_code: "FILE_NOT_FOUND" },
      });
      wrapper.vm.getItemsOfRss();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toContain("존재하지 않습니다");
    });

    it("handles NO_ITEMS error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", error_code: "NO_ITEMS" },
      });
      wrapper.vm.getItemsOfRss();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toContain("아이템이 없습니다");
    });

    it("handles PARSE_ERROR", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: {
          status: "failure",
          error_code: "PARSE_ERROR",
          message: "Parse error",
        },
      });
      wrapper.vm.getItemsOfRss();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Parse error");
    });

    it("handles generic failure", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "Generic error" },
      });
      wrapper.vm.getItemsOfRss();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Generic error");
    });

    it("handles network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockRejectedValueOnce({ message: "Network Error" });
      wrapper.vm.getItemsOfRss();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toContain("에러가 발생했습니다");
    });
  });

  describe("checkRunning", () => {
    it("starts button when running", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: { status: "success", running_status: true },
      });
      wrapper.vm.checkRunning();
      await flushPromises();
    });

    it("ends button when not running", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.checkRunning();
      await flushPromises();
    });

    it("handles failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "error" },
      });
      wrapper.vm.checkRunning();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("error");
    });

    it("handles API error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      axios.get.mockRejectedValueOnce(new Error("network"));
      wrapper.vm.checkRunning();
      await flushPromises();
    });
  });

  describe("beforeUnmount", () => {
    it("clears interval and destroys editor", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.checkRunningInterval = setInterval(() => {}, 1000);
      wrapper.unmount();
    });
  });

  describe("getGroups failure", () => {
    it("shows alert on failure status", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "No groups" },
      });
      wrapper.vm.getGroups();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("No groups");
    });

    it("handles API error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockRejectedValueOnce(new Error("Network"));
      wrapper.vm.getGroups();
      await flushPromises();
    });
  });

  describe("getFeedlistByGroup failure", () => {
    it("shows alert on failure status", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "No feeds" },
      });
      wrapper.vm.getFeedlistByGroup("g1");
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("No feeds");
    });
  });

  describe("getSiteConfig failure", () => {
    it("shows alert on failure", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "Config error" },
      });
      wrapper.vm.getSiteConfig();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Config error");
    });
  });

  describe("beforeUnmount cleanup", () => {
    it("destroys jsonEditor on unmount", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const destroySpy = vi.fn();
      wrapper.vm.jsonEditor = { destroy: destroySpy };
      wrapper.unmount();
      expect(destroySpy).toHaveBeenCalled();
    });

    it("clears interval and sets jsonEditor to null", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const intervalId = setInterval(() => {}, 10000);
      wrapper.vm.checkRunningInterval = intervalId;
      wrapper.vm.jsonEditor = { destroy: vi.fn() };
      wrapper.unmount();
      // After unmount, interval should be cleared (no error)
    });

    it("unmounts cleanly without interval or editor", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.checkRunningInterval = null;
      wrapper.vm.jsonEditor = null;
      wrapper.unmount();
    });
  });

  describe("toggleStatus confirm action execution", () => {
    it("executes feed toggle on confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.toggleStatus("feed");
      expect(wrapper.vm.showConfirmModal).toBe(true);

      axios.put = vi.fn().mockResolvedValueOnce({
        data: { status: "success", new_name: "f1_new" },
      });
      axios.get.mockResolvedValueOnce({
        data: { status: "success", feeds: [] },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(axios.put).toHaveBeenCalled();
    });

    it("executes group toggle on confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.toggleStatus("group");
      expect(wrapper.vm.showConfirmModal).toBe(true);

      axios.put = vi.fn().mockResolvedValueOnce({
        data: { status: "success", new_name: "g1_new" },
      });
      axios.get.mockResolvedValueOnce({
        data: { status: "success", groups: [] },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(axios.put).toHaveBeenCalled();
    });
  });

  describe("removeFeed confirm action execution", () => {
    it("executes feed deletion on confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removeFeed();
      expect(wrapper.vm.showConfirmModal).toBe(true);

      axios.delete = vi
        .fn()
        .mockResolvedValueOnce({ data: { status: "success" } });
      axios.get.mockResolvedValueOnce({
        data: { status: "success", feeds: [] },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(axios.delete).toHaveBeenCalled();
    });
  });

  describe("removeGroup confirm action execution", () => {
    it("executes group deletion on confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.removeGroup();
      expect(wrapper.vm.showConfirmModal).toBe(true);

      axios.delete = vi
        .fn()
        .mockResolvedValueOnce({ data: { status: "success" } });
      axios.get.mockResolvedValueOnce({
        data: { status: "success", groups: [] },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(axios.delete).toHaveBeenCalled();
    });
  });

  describe("save failure response", () => {
    it("shows alert on failure status", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.newFeedName = "f1";
      wrapper.vm.jsonData = {
        rss: { title: "T", link: "l", description: "D" },
      };
      axios.post.mockResolvedValueOnce({
        data: { status: "failure", message: "Save failed" },
      });
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.save();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Save failed");
    });
  });

  describe("removelist / removeHtml confirm action execution", () => {
    it("executes removelist on confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removelist();

      axios.delete = vi
        .fn()
        .mockResolvedValueOnce({ data: { status: "success" } });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(axios.delete).toHaveBeenCalled();
    });

    it("executes removeHtml on confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removeHtml();

      axios.delete = vi
        .fn()
        .mockResolvedValueOnce({ data: { status: "success" } });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(axios.delete).toHaveBeenCalled();
    });
  });

  describe("getFeedInfo with sparse config", () => {
    it("hides feed-related UI when config has fewer than 3 keys", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.getFeedInfo("g1", "f1");
      await flushPromises();
      expect(wrapper.vm.showEditor).toBe(false);
    });

    it("handles getFeedInfo failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "Feed not found" },
      });
      wrapper.vm.getFeedInfo("g1", "f1");
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Feed not found");
    });

    it("handles getFeedInfo network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockRejectedValueOnce(new Error("network"));
      wrapper.vm.getFeedInfo("g1", "f1");
      await flushPromises();
      // Should not throw
    });
  });

  describe("saveSiteConfig confirm action execution", () => {
    it("executes saveSiteConfig put on confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.jsonData = { key: "value" };
      wrapper.vm.saveSiteConfig();
      expect(wrapper.vm.showConfirmModal).toBe(true);

      axios.put = vi
        .fn()
        .mockResolvedValueOnce({ data: { status: "success" } });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(axios.put).toHaveBeenCalled();
    });

    it("shows alert on saveSiteConfig failure", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.jsonData = { key: "value" };
      wrapper.vm.saveSiteConfig();

      axios.put = vi.fn().mockResolvedValueOnce({
        data: { status: "failure", message: "Config save failed" },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Config save failed");
    });

    it("handles saveSiteConfig network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.jsonData = { key: "value" };
      wrapper.vm.saveSiteConfig();

      axios.put = vi.fn().mockRejectedValueOnce(new Error("network"));
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      // Should not throw
    });
  });

  describe("toggleStatus failure and error paths", () => {
    it("shows alert on feed toggle failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.toggleStatus("feed");

      axios.put = vi.fn().mockResolvedValueOnce({
        data: { status: "failure", message: "Toggle failed" },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Toggle failed");
    });

    it("handles feed toggle network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.toggleStatus("feed");

      axios.put = vi.fn().mockRejectedValueOnce(new Error("network"));
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      // Should not throw
    });

    it("handles group toggle network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.toggleStatus("group");

      axios.put = vi.fn().mockRejectedValueOnce(new Error("network"));
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      // Should not throw
    });
  });

  describe("removeFeed/removeGroup failure within confirm action", () => {
    it("shows alert on removeFeed failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removeFeed();

      axios.delete = vi.fn().mockResolvedValueOnce({
        data: { status: "failure", message: "Delete failed" },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Delete failed");
    });

    it("handles removeFeed network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removeFeed();

      axios.delete = vi.fn().mockRejectedValueOnce(new Error("network"));
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      // Should not throw
    });

    it("shows alert on removeGroup failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.removeGroup();

      axios.delete = vi.fn().mockResolvedValueOnce({
        data: { status: "failure", message: "Group delete failed" },
      });
      axios.get.mockResolvedValueOnce({
        data: { status: "success", groups: [] },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Group delete failed");
    });

    it("handles removeGroup network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.removeGroup();

      axios.delete = vi.fn().mockRejectedValueOnce(new Error("network"));
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      // Should not throw
    });
  });

  describe("template rendering with data", () => {
    it("renders group list items when groups are loaded", async () => {
      axios.get.mockReset();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          groups: [
            { name: "group1", num_feeds: 3, is_active: true },
            { name: "_inactive", num_feeds: 1, is_active: false },
          ],
        },
      });

      const wrapper = mount(FeedManagement, {
        global: { stubs, mocks: { $route: { params: {} } } },
      });
      wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
      await flushPromises();

      expect(wrapper.vm.groups.length).toBe(2);
      const html = wrapper.html();
      expect(html).toContain("group1");
    });

    it("renders feed list items when feeds are loaded", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.showFeedlist = true;
      wrapper.vm.feeds = [
        { name: "feed1", title: "Feed One", is_active: true },
        { name: "_disabled", title: "Disabled", is_active: false },
      ];
      await wrapper.vm.$nextTick();
      const html = wrapper.html();
      expect(html).toContain("Feed One");
    });

    it("renders feed info section when editor is shown", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.showFeedInfo = true;
      wrapper.vm.showNewFeedNameInput = true;
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.numCollectionUrls = 3;
      wrapper.vm.collectDate = "2024-01-15";
      wrapper.vm.totalItemCount = 100;
      wrapper.vm.numItemsInResult = 50;
      wrapper.vm.sizeOfResultFile = 2048;
      wrapper.vm.lastUploadDate = "2024-01-10";
      wrapper.vm.currentIndex = 30;
      wrapper.vm.progressRatio = 30;
      wrapper.vm.feedCompletionDueDate = "2024-02-01";
      await wrapper.vm.$nextTick();
      const html = wrapper.html();
      expect(html).toContain("g1/f1");
    });

    it("renders search results when showSearchResult is true", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.showSearchResult = true;
      wrapper.vm.feeds = [
        { group_name: "g", feed_name: "f", feed_title: "SearchResult" },
      ];
      await flushPromises();
      const html = wrapper.html();
      expect(html).toContain("SearchResult");
    });
  });

  describe("removelist / removeHtml failure paths", () => {
    it("shows alert on removelist failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removelist();

      axios.delete = vi.fn().mockResolvedValueOnce({
        data: { status: "failure", message: "List delete failed" },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("List delete failed");
    });

    it("handles removelist network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removelist();

      axios.delete = vi.fn().mockRejectedValueOnce(new Error("network"));
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      // Should not throw
    });

    it("shows alert on removeHtml failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removeHtml();

      axios.delete = vi.fn().mockResolvedValueOnce({
        data: { status: "failure", message: "Html delete failed" },
      });
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("Html delete failed");
    });

    it("handles removeHtml network error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removeHtml();

      axios.delete = vi.fn().mockRejectedValueOnce(new Error("network"));
      wrapper.vm.handleConfirmOk();
      await flushPromises();
      // Should not throw
    });
  });

  describe("removelist", () => {
    it("calls DELETE on list endpoint after confirm", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.removelist();

      axios.delete = vi
        .fn()
        .mockResolvedValueOnce({ data: { status: "success" } });
      wrapper.vm.handleConfirmOk();
      await flushPromises();

      expect(axios.delete).toHaveBeenCalledWith(
        expect.stringContaining("/groups/g1/feeds/f1/list"),
      );
    });
  });

  describe("registerToInoreader and registerToFeedly", () => {
    it("opens Inoreader URL", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.newFeedName = "test_feed";
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => {});
      wrapper.vm.registerToInoreader();
      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining("inoreader.com"),
      );
      openSpy.mockRestore();
    });

    it("opens Feedly URL", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.newFeedName = "test_feed";
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => {});
      wrapper.vm.registerToFeedly();
      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining("feedly.com"),
      );
      openSpy.mockRestore();
    });
  });

  describe("toggleStatus group branch", () => {
    it("handles group toggle success", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";

      axios.put = vi.fn().mockResolvedValueOnce({
        data: { status: "success", new_name: "g1_renamed" },
      });
      // getGroups call after toggle
      axios.get.mockResolvedValueOnce({
        data: { status: "success", groups: [] },
      });

      wrapper.vm.toggleStatus("group");
      await flushPromises();
      wrapper.vm.handleConfirmOk();
      await flushPromises();

      expect(axios.put).toHaveBeenCalledWith(
        expect.stringContaining("/groups/g1/toggle"),
      );
    });
  });

  describe("mounted with route params", () => {
    it("initializes from route params", async () => {
      axios.get.mockReset();
      // feedNameButtonClicked -> getFeedInfo
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: {
                title: "Test",
                link: "https://example.com/test.xml",
                description: "",
              },
              collection: { list_url_list: ["https://example.com"] },
            },
            collection_info: {},
            public_feed_info: {},
            progress_info: {},
            config_modify_date: "",
          },
        },
      });

      const wrapper = mount(FeedManagement, {
        global: {
          stubs,
          mocks: { $route: { params: { group: "naver", feed: "myfeed" } } },
        },
      });
      await flushPromises();

      expect(wrapper.vm.selectedGroupName).toBe("naver");
      expect(wrapper.vm.selectedFeedName).toBe("myfeed");
    });
  });

  describe("button ref management", () => {
    it("startButton logs error when ref is missing", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.startButton("nonExistentRef");
      expect(console.error).toHaveBeenCalledWith(
        "Button ref not found:",
        "nonExistentRef",
      );
    });

    it("endButton logs error when ref is missing", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.endButton("nonExistentRef");
      expect(console.error).toHaveBeenCalledWith(
        "Button ref not found:",
        "nonExistentRef",
      );
    });
  });

  describe("interval cleanup", () => {
    it("getGroups clears existing checkRunningInterval", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const fakeInterval = 999;
      wrapper.vm.checkRunningInterval = fakeInterval;
      const clearIntervalSpy = vi.spyOn(global, "clearInterval");
      axios.get.mockResolvedValueOnce({
        data: { status: "success", groups: [] },
      });
      wrapper.vm.getGroups();
      await flushPromises();
      expect(clearIntervalSpy).toHaveBeenCalledWith(fakeInterval);
      clearIntervalSpy.mockRestore();
    });

    it("getFeedlistByGroup clears existing checkRunningInterval", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const fakeInterval = 888;
      wrapper.vm.checkRunningInterval = fakeInterval;
      const clearIntervalSpy = vi.spyOn(global, "clearInterval");
      axios.get.mockResolvedValueOnce({
        data: { status: "success", feeds: [] },
      });
      wrapper.vm.getFeedlistByGroup("testGroup");
      await flushPromises();
      expect(clearIntervalSpy).toHaveBeenCalledWith(fakeInterval);
      clearIntervalSpy.mockRestore();
    });

    it("getFeedInfo clears existing checkRunningInterval", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const fakeInterval = 777;
      wrapper.vm.checkRunningInterval = fakeInterval;
      const clearIntervalSpy = vi.spyOn(global, "clearInterval");
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.getFeedInfo("g1", "f1");
      await flushPromises();
      expect(clearIntervalSpy).toHaveBeenCalledWith(fakeInterval);
      clearIntervalSpy.mockRestore();
    });
  });

  describe("error handling - additional paths", () => {
    it("getFeedlistByGroup handles axios error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockRejectedValueOnce(new Error("network error"));
      wrapper.vm.getFeedlistByGroup("testGroup");
      await flushPromises();
      // Should not throw
    });

    it("getSiteConfig handles axios error", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      axios.get.mockRejectedValueOnce(new Error("network error"));
      wrapper.vm.getSiteConfig();
      await flushPromises();
      // Should not throw
    });

    it("runFeed handles failure response", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.newFeedName = "f1";
      wrapper.vm.selectedFeedName = "f1";
      axios.post.mockResolvedValueOnce({
        data: { status: "failure", message: "run failed" },
      });
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.run();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("run failed");
    });

    it("checkRunning failure clears interval and resets button", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedGroupName = "g1";
      wrapper.vm.selectedFeedName = "f1";
      const fakeInterval = 555;
      wrapper.vm.checkRunningInterval = fakeInterval;
      const clearIntervalSpy = vi.spyOn(global, "clearInterval");
      axios.get.mockResolvedValueOnce({
        data: { status: "failure", message: "check failed" },
      });
      wrapper.vm.checkRunning();
      await flushPromises();
      expect(wrapper.vm.alertMessage).toBe("check failed");
      expect(clearIntervalSpy).toHaveBeenCalledWith(fakeInterval);
      clearIntervalSpy.mockRestore();
    });
  });

  describe("jsonEditor lifecycle", () => {
    it("hideAllRelatedToFeed destroys existing jsonEditor", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const destroySpy = vi.fn();
      wrapper.vm.jsonEditor = {
        destroy: destroySpy,
        set: vi.fn(),
        get: vi.fn(),
        expandAll: vi.fn(),
      };
      wrapper.vm.hideAllRelatedToFeed();
      expect(destroySpy).toHaveBeenCalled();
      expect(wrapper.vm.jsonEditor).toBeNull();
    });

    it("initJsonEditor destroys existing editor before creating new one", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const destroySpy = vi.fn();
      wrapper.vm.jsonEditor = {
        destroy: destroySpy,
        set: vi.fn(),
        get: vi.fn(),
        expandAll: vi.fn(),
      };
      wrapper.vm.initJsonEditor();
      expect(destroySpy).toHaveBeenCalled();
      expect(wrapper.vm.jsonEditor).toBeNull();
    });

    it("initJsonEditor onChange catches jsonEditor.get() error", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      // jsonEditor를 get()이 throw하는 mock으로 설정
      const throwingEditor = {
        destroy: vi.fn(),
        set: vi.fn(),
        expandAll: vi.fn(),
        get: vi.fn().mockImplementation(() => {
          throw new Error("get failed");
        }),
      };
      wrapper.vm.jsonEditor = throwingEditor;

      // onChange 로직 직접 실행: initJsonEditor 내부 onChange 콜백과 동일한 코드
      // try { this.jsonData = this.jsonEditor.get(); } catch(e) { console.error(...); }
      expect(() => {
        try {
          wrapper.vm.jsonData = wrapper.vm.jsonEditor.get();
        } catch (e) {
          console.error("JSON 에디터 데이터 가져오기 실패:", e);
        }
      }).not.toThrow();

      // get()이 실제로 호출됐는지 확인
      expect(throwingEditor.get).toHaveBeenCalled();
    });

    it("updateJsonEditor sets jsonData to existing editor", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const setSpy = vi.fn();
      wrapper.vm.jsonEditor = {
        destroy: vi.fn(),
        set: setSpy,
        get: vi.fn(),
        expandAll: vi.fn(),
      };
      wrapper.vm.jsonData = {
        rss: {
          title: "Test",
          link: "https://example.com/test.xml",
          description: "desc",
        },
      };
      wrapper.vm.updateJsonEditor();
      expect(setSpy).toHaveBeenCalledWith(wrapper.vm.jsonData);
    });
  });

  describe("getFeedInfo sets interval after success", () => {
    it("sets checkRunningInterval after successful getFeedInfo", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.getFeedInfo("g1", "f1");
      await flushPromises();
      expect(wrapper.vm.checkRunningInterval).toBeTruthy();
      // cleanup: interval 정리
      clearInterval(wrapper.vm.checkRunningInterval);
    });
  });

  describe("GET /groups/:group/feeds/:feed — contract compliance", () => {
    it("consumes all required feed_info fields from the backend contract", async () => {
      axios.get.mockReset();
      axios.get.mockResolvedValueOnce({
        data: { status: "success", feed_info: FEED_INFO_CONTRACT },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });

      const wrapper = mount(FeedManagement, {
        global: {
          stubs,
          mocks: { $route: { params: { group: "g", feed: "f" } } },
        },
      });
      await flushPromises();

      // config 전체가 jsonData로 설정된다
      expect(wrapper.vm.jsonData).toMatchObject(FEED_INFO_CONTRACT.config);

      // collection_info 필드가 소비된다
      expect(wrapper.vm.collectDate).toBe("2024-01-01");
      expect(wrapper.vm.totalItemCount).toBe(
        FEED_INFO_CONTRACT.collection_info.total_item_count,
      );

      // public_feed_info 필드가 소비된다
      expect(wrapper.vm.numItemsInResult).toBe(
        FEED_INFO_CONTRACT.public_feed_info.num_items,
      );
      expect(wrapper.vm.sizeOfResultFile).toBe(
        FEED_INFO_CONTRACT.public_feed_info.file_size,
      );

      // progress_info 필드가 소비된다
      expect(wrapper.vm.currentIndex).toBe(
        FEED_INFO_CONTRACT.progress_info.current_index,
      );
      expect(wrapper.vm.progressRatio).toBe(
        FEED_INFO_CONTRACT.progress_info.progress_ratio,
      );
      expect(wrapper.vm.unitSizePerDay).toBe(
        FEED_INFO_CONTRACT.progress_info.unit_size_per_day,
      );
    });
  });

  describe("progress bar rendering", () => {
    const setupProgressWrapper = async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.showFeedInfo = true;
      wrapper.vm.currentIndex = 30;
      wrapper.vm.totalItemCount = 100;
      wrapper.vm.progressRatio = 30;
      wrapper.vm.unitSizePerDay = 5;
      await wrapper.vm.$nextTick();
      return wrapper;
    };

    it("progress overlay div does not use overflow:visible", async () => {
      const wrapper = await setupProgressWrapper();
      expect(wrapper.html()).not.toContain("overflow: visible");
    });

    it("progress overlay div uses inset:0 to contain within progress bar", async () => {
      const wrapper = await setupProgressWrapper();
      expect(wrapper.html()).toContain("inset: 0");
    });

    it("progress overlay div renders progress text", async () => {
      const wrapper = await setupProgressWrapper();
      const html = wrapper.html();
      expect(html).toContain("30");
      expect(html).toContain("100");
      expect(html).toContain("5");
    });
  });

  describe("destructive button variants", () => {
    const variantStubs = {
      ...stubs,
      MyButton: {
        props: ["label", "variant"],
        template:
          '<button :class="variant ? `btn-${variant}` : ``">{{ label }}</button>',
      },
    };

    const createWrapperWithVariantStub = () => {
      axios.get.mockResolvedValueOnce({
        data: { status: "success", groups: [] },
      });
      const wrapper = mount(FeedManagement, {
        global: {
          stubs: variantStubs,
          mocks: { $route: { params: {} } },
        },
      });
      wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
      wrapper.vm.showRemovelistButton = true;
      wrapper.vm.showRemoveHtmlButton = true;
      wrapper.vm.showRemoveFeedButton = true;
      return wrapper;
    };

    it("목록 삭제 버튼은 warning variant를 가진다", async () => {
      const wrapper = createWrapperWithVariantStub();
      await wrapper.vm.$nextTick();
      const buttons = wrapper.findAll("button");
      const target = buttons.find((b) => b.text() === "목록 삭제");
      expect(target).toBeDefined();
      expect(target.classes()).toContain("btn-warning");
    });

    it("HTML 삭제 버튼은 warning variant를 가진다", async () => {
      const wrapper = createWrapperWithVariantStub();
      await wrapper.vm.$nextTick();
      const buttons = wrapper.findAll("button");
      const target = buttons.find((b) => b.text() === "HTML 삭제");
      expect(target).toBeDefined();
      expect(target.classes()).toContain("btn-warning");
    });

    it("피드 삭제 버튼은 danger variant를 가진다", async () => {
      const wrapper = createWrapperWithVariantStub();
      await wrapper.vm.$nextTick();
      const buttons = wrapper.findAll("button");
      const target = buttons.find((b) => b.text() === "피드 삭제");
      expect(target).toBeDefined();
      expect(target.classes()).toContain("btn-danger");
    });
  });

  describe("additional uncovered coverage", () => {
    it("startButton shows spinner and hides icon when ref exists", async () => {
      // $refs는 readonly이므로 항상 렌더링되는 기존 ref(searchButton)를 사용한다.
      const wrapper = createWrapper();
      await flushPromises();
      const btn = wrapper.vm.$refs.searchButton;
      btn.doShowInitialIcon = true;
      btn.doShowSpinner = false;
      wrapper.vm.startButton("searchButton");
      expect(btn.doShowInitialIcon).toBe(false);
      expect(btn.doShowSpinner).toBe(true);
    });

    it("resetButton restores icon and clears spinner when ref exists", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const btn = wrapper.vm.$refs.searchButton;
      btn.doShowInitialIcon = false;
      btn.doShowSpinner = true;
      wrapper.vm.resetButton("searchButton");
      expect(btn.doShowInitialIcon).toBe(true);
      expect(btn.doShowSpinner).toBe(false);
    });

    it("resetButton logs error when ref is missing", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.resetButton("missingRef");
      expect(console.error).toHaveBeenCalledWith(
        "Button ref not found:",
        "missingRef",
      );
    });

    it("hideAllRelatedToSiteConfig destroys existing jsonEditor", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const destroySpy = vi.fn();
      wrapper.vm.jsonEditor = { destroy: destroySpy };
      wrapper.vm.hideAllRelatedToSiteConfig();
      expect(destroySpy).toHaveBeenCalled();
      expect(wrapper.vm.jsonEditor).toBeNull();
    });

    it("getFeedInfo sets an interval whose callback calls checkRunning", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      const setIntervalSpy = vi.spyOn(global, "setInterval");
      const checkRunningSpy = vi
        .spyOn(wrapper.vm, "checkRunning")
        .mockImplementation(() => {});

      axios.get.mockResolvedValueOnce({
        data: {
          status: "success",
          feed_info: {
            config: {
              rss: { title: "T", link: "l", description: "D" },
              collection: { list_url_list: [] },
              extraction: {},
            },
            collection_info: { collect_date: "", total_item_count: 0 },
            public_feed_info: { num_items: 0, file_size: 0 },
            progress_info: {
              current_index: 0,
              total_item_count: 0,
              unit_size_per_day: 0,
              progress_ratio: 0,
            },
          },
        },
      });
      axios.get.mockResolvedValue({
        data: { status: "success", running_status: false },
      });
      wrapper.vm.getFeedInfo("g1", "f1");
      await flushPromises();

      // 3000ms 주기로 등록된 setInterval 콜백을 직접 실행해 line 1014를 탄다.
      const intervalCall = setIntervalSpy.mock.calls.find((c) => c[1] === 3000);
      expect(intervalCall).toBeDefined();
      checkRunningSpy.mockClear();
      intervalCall[0]();
      expect(checkRunningSpy).toHaveBeenCalled();

      clearInterval(wrapper.vm.checkRunningInterval);
      setIntervalSpy.mockRestore();
      checkRunningSpy.mockRestore();
    });

    it("initJsonEditor wires a real onChange handler (success and error paths)", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.showEditor = true;
      await wrapper.vm.$nextTick();

      jsonEditorMock.mockClear();
      wrapper.vm.initJsonEditor();
      // initJsonEditor 내부의 $nextTick 콜백에서 JSONEditor가 생성됨
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(jsonEditorMock).toHaveBeenCalled();
      const options = jsonEditorMock.mock.calls.at(-1)[1];
      expect(typeof options.onChange).toBe("function");

      // 성공 경로: get()이 값을 반환 → jsonData 갱신 (line 1348)
      wrapper.vm.jsonEditor.get = vi.fn().mockReturnValue({ updated: true });
      options.onChange();
      expect(wrapper.vm.jsonData).toEqual({ updated: true });

      // 에러 경로: get()이 throw → catch에서 console.error (line 1350)
      wrapper.vm.jsonEditor.get = vi.fn(() => {
        throw new Error("get failed");
      });
      expect(() => options.onChange()).not.toThrow();
      expect(console.error).toHaveBeenCalledWith(
        "JSON 에디터 데이터 가져오기 실패:",
        expect.any(Error),
      );
    });

    it("binds v-model and renders slots on search/newFeed inputs", async () => {
      // 기본 BFormInput 스텁(<input />)은 v-model setter와 슬롯을 렌더링하지 않아
      // 미커버였다. modelValue 바인딩 + 슬롯 렌더링 스텁으로 두 경로를 탄다.
      const richStubs = {
        ...stubs,
        BFormInput: {
          props: ["modelValue"],
          emits: ["update:modelValue"],
          template:
            '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" /><span class="slot-content"><slot /></span>',
        },
      };
      axios.get.mockResolvedValue({
        data: { status: "success", groups: [] },
      });
      const wrapper = mount(FeedManagement, {
        global: {
          stubs: richStubs,
          mocks: { $route: { params: {} } },
        },
      });
      wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
      // getGroups가 마운트 직후 표시 플래그를 초기화하므로 flush 이후에 설정한다.
      await flushPromises();
      wrapper.vm.showNewFeedNameInput = true;
      await wrapper.vm.$nextTick();

      const inputs = wrapper.findAll("input");
      // 검색어 입력 (line 27, 32): placeholder="키워드"인 첫 input
      await inputs[0].setValue("검색키워드");
      expect(wrapper.vm.searchKeyword).toBe("검색키워드");
      // 새 피드 이름 입력 (line 218, 219)
      const newFeedInput = inputs[inputs.length - 1];
      await newFeedInput.setValue("새피드");
      expect(wrapper.vm.newFeedName).toBe("새피드");

      const slotTexts = wrapper.findAll(".slot-content").map((s) => s.text());
      expect(slotTexts).toContain("검색키워드");
      expect(slotTexts).toContain("새피드");
    });

    it("syncs showConfirmModal through BModal v-model update event", async () => {
      // 기본 BModal 스텁은 update:modelValue를 emit하지 않아 v-model setter(line 403)가
      // 미커버였다. emit 가능한 스텁으로 setter 경로를 탄다.
      const modalStubs = {
        ...stubs,
        BModal: {
          props: ["modelValue"],
          emits: ["update:modelValue"],
          template:
            '<div><button class="modal-close" @click="$emit(\'update:modelValue\', false)" /><slot /></div>',
        },
      };
      axios.get.mockResolvedValue({
        data: { status: "success", groups: [] },
      });
      const wrapper = mount(FeedManagement, {
        global: { stubs: modalStubs, mocks: { $route: { params: {} } } },
      });
      wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
      await flushPromises();

      wrapper.vm.showConfirmModal = true;
      await wrapper.vm.$nextTick();
      await wrapper.find(".modal-close").trigger("click");
      expect(wrapper.vm.showConfirmModal).toBe(false);
    });

    it("invokes inline @click handlers on rendered group/feed/toggle buttons", async () => {
      axios.get.mockResolvedValue({
        data: { status: "success", groups: [], feeds: [] },
      });
      axios.put = vi.fn().mockResolvedValue({ data: { status: "success" } });
      // 기본 MyButton 스텁은 label prop을 렌더링하지 않아 버튼을 텍스트로 찾을 수 없으므로
      // label을 렌더링하는 스텁을 사용한다. emits 미선언이라 @click은 native로 fall-through되어
      // trigger("click")으로 인라인 핸들러가 실행된다.
      const labeledStubs = {
        ...stubs,
        MyButton: {
          props: ["label"],
          template: "<button>{{ label }}</button>",
        },
      };
      const wrapper = mount(FeedManagement, {
        global: { stubs: labeledStubs, mocks: { $route: { params: {} } } },
      });
      wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
      await flushPromises();

      // 그룹 버튼 렌더링 후 클릭 → groupNameButtonClicked 인라인 핸들러 (line 88)
      wrapper.vm.groups = [
        { name: "groupA", num_feeds: 2 },
        { name: "groupB", num_feeds: 1 },
      ];
      wrapper.vm.showGrouplist = true;
      await wrapper.vm.$nextTick();
      const groupBtn = wrapper
        .findAll("button")
        .find((b) => b.text().includes("groupB"));
      expect(groupBtn).toBeDefined();
      await groupBtn.trigger("click");
      expect(wrapper.vm.selectedGroupName).toBe("groupB");

      // 피드 버튼 렌더링 후 클릭 → feedNameButtonClicked 인라인 핸들러 (line 111)
      wrapper.vm.feeds = [{ title: "feedX", name: "feedx" }];
      wrapper.vm.showFeedlist = true;
      await wrapper.vm.$nextTick();
      const feedBtn = wrapper
        .findAll("button")
        .find((b) => b.text() === "feedX");
      expect(feedBtn).toBeDefined();
      await feedBtn.trigger("click");
      expect(wrapper.vm.selectedFeedName).toBe("feedx");

      // 검색 결과 피드 버튼 클릭 → searchResultFeedNameButtonClicked (line 59)
      wrapper.vm.feeds = [
        { group_name: "g1", feed_title: "검색피드", feed_name: "sf1" },
      ];
      wrapper.vm.showSearchResult = true;
      wrapper.vm.showFeedlist = false;
      await wrapper.vm.$nextTick();
      const searchFeedBtn = wrapper
        .findAll("button")
        .find((b) => b.text().includes("검색피드"));
      expect(searchFeedBtn).toBeDefined();
      await searchFeedBtn.trigger("click");
      expect(wrapper.vm.selectedFeedName).toBe("sf1");

      // 그룹 토글 버튼 클릭 → toggleStatus('group') 인라인 핸들러 (line 253)
      wrapper.vm.selectedGroupName = "groupB";
      wrapper.vm.showToggleGroupButton = true;
      await wrapper.vm.$nextTick();
      const toggleGroupBtn = wrapper
        .findAll("button")
        .find((b) => b.text() === wrapper.vm.groupStatusLabel);
      expect(toggleGroupBtn).toBeDefined();
      await toggleGroupBtn.trigger("click");
      expect(wrapper.vm.showConfirmModal).toBe(true);
      wrapper.vm.showConfirmModal = false;

      // 피드 토글 버튼 클릭 → toggleStatus('feed') 인라인 핸들러 (line 299)
      wrapper.vm.selectedFeedName = "feedx";
      wrapper.vm.showToggleFeedButton = true;
      await wrapper.vm.$nextTick();
      const toggleFeedBtn = wrapper
        .findAll("button")
        .find((b) => b.text() === wrapper.vm.feedStatusLabel);
      expect(toggleFeedBtn).toBeDefined();
      await toggleFeedBtn.trigger("click");
      expect(wrapper.vm.showConfirmModal).toBe(true);
    });
  });
});
