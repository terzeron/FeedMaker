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

const createWrapper = (mountOptions = {}) => {
  axios.get.mockResolvedValueOnce({ data: { status: "success", groups: [] } });
  const wrapper = mount(FeedManagement, {
    global: {
      stubs,
      mocks: { $route: { params: {} } },
    },
    ...mountOptions,
  });
  wrapper.vm.jsonData = { rss: { title: "", link: "", description: "" } };
  return wrapper;
};

describe("FeedManagement.vue - 미커버 분기", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    console.log.mockRestore();
    console.error.mockRestore();
  });

  describe("status label/icon computed", () => {
    it("비활성 피드/그룹이 선택되면 '활성화' 라벨과 'toggle-on' 아이콘을 반환한다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.feeds = [{ name: "f1", is_active: false }];
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.groups = [{ name: "g1", is_active: false }];
      wrapper.vm.selectedGroupName = "g1";
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.feedStatus).toBe(false);
      expect(wrapper.vm.groupStatus).toBe(false);
      expect(wrapper.vm.feedStatusLabel).toBe("피드 활성화");
      expect(wrapper.vm.feedStatusIcon).toBe("toggle-on");
      expect(wrapper.vm.groupStatusLabel).toBe("그룹 활성화");
      expect(wrapper.vm.groupStatusIcon).toBe("toggle-on");
    });

    it("그룹만 비활성이면 그룹 아이콘만 뒤집힌다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.feeds = [{ name: "f1", is_active: true }];
      wrapper.vm.selectedFeedName = "f1";
      wrapper.vm.groups = [{ name: "g1", is_active: false }];
      wrapper.vm.selectedGroupName = "g1";
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.feedStatusIcon).toBe("toggle-off");
      expect(wrapper.vm.groupStatusIcon).toBe("toggle-on");
    });
  });

  describe("getGroups", () => {
    it("응답에 groups 필드가 없으면 빈 배열로 초기화한다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.groups = [{ name: "stale" }];
      axios.get.mockResolvedValueOnce({ data: { status: "success" } });
      wrapper.vm.getGroups();
      await flushPromises();

      expect(wrapper.vm.groups).toEqual([]);
    });
  });

  describe("groupNameButtonClicked", () => {
    it("index가 falsy면 activeGroupIndex를 갱신하지 않는다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.activeGroupIndex = undefined;
      axios.get.mockResolvedValueOnce({
        data: { status: "success", feeds: [] },
      });
      wrapper.vm.groupNameButtonClicked("g1", 0);
      await flushPromises();

      expect(wrapper.vm.selectedGroupName).toBe("g1");
      expect(wrapper.vm.activeGroupIndex).toBeUndefined();
    });
  });

  describe("getFeedlistByGroup", () => {
    it("응답에 feeds 필드가 없으면 빈 배열로 초기화한다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.feeds = [{ name: "stale" }];
      axios.get.mockResolvedValueOnce({ data: { status: "success" } });
      wrapper.vm.getFeedlistByGroup("g1");
      await flushPromises();

      expect(wrapper.vm.feeds).toEqual([]);
    });
  });

  describe("getSiteConfig", () => {
    it("configuration 키가 2개 미만이면 site config 영역을 열지 않는다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      const showSpy = vi.spyOn(wrapper.vm, "showAllRelatedToSiteConfig");
      axios.get.mockResolvedValueOnce({
        data: { status: "success", configuration: { url: "https://a" } },
      });
      wrapper.vm.getSiteConfig();
      await flushPromises();

      expect(wrapper.vm.jsonData).toEqual({ url: "https://a" });
      expect(showSpy).not.toHaveBeenCalled();
    });
  });

  describe("getItemsOfRss", () => {
    it("PARSE_ERROR에 message가 없으면 기본 메시지를 표시한다", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";

      axios.get.mockResolvedValueOnce({
        data: { status: "failure", error_code: "PARSE_ERROR" },
      });
      wrapper.vm.getItemsOfRss();
      await flushPromises();

      expect(wrapper.vm.alertMessage).toBe("알 수 없는 에러가 발생했습니다.");
    });

    it("error_code와 message가 모두 없으면 기본 실패 메시지를 표시한다", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";

      axios.get.mockResolvedValueOnce({ data: { status: "failure" } });
      wrapper.vm.getItemsOfRss();
      await flushPromises();

      expect(wrapper.vm.alertMessage).toBe("데이터를 가져오는데 실패했습니다.");
    });

    it("error.response가 있으면 HTTP status를 메시지에 포함한다", async () => {
      const wrapper = createWrapper();
      await flushPromises();
      wrapper.vm.selectedFeedName = "f1";

      axios.get.mockRejectedValueOnce({ response: { status: 500 } });
      wrapper.vm.getItemsOfRss();
      await flushPromises();

      expect(wrapper.vm.alertMessage).toBe(
        "요청 처리 중 에러가 발생했습니다: 500",
      );
    });
  });

  describe("json editor", () => {
    it("jsonData가 비어 있으면 에디터에 값을 설정하지 않는다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.jsonData = {};
      wrapper.vm.showEditor = true;
      await wrapper.vm.$nextTick();

      jsonEditorMock.mockClear();
      wrapper.vm.initJsonEditor();
      await wrapper.vm.$nextTick();
      await flushPromises();

      expect(jsonEditorMock).toHaveBeenCalledTimes(1);
      expect(wrapper.vm.jsonEditor.set).not.toHaveBeenCalled();
      expect(wrapper.vm.jsonEditor.expandAll).not.toHaveBeenCalled();
    });

    it("jsonEditor가 없으면 updateJsonEditor는 아무 것도 하지 않는다", async () => {
      const wrapper = createWrapper();
      await flushPromises();

      wrapper.vm.jsonEditor = null;
      expect(() => wrapper.vm.updateJsonEditor()).not.toThrow();
    });
  });

  describe("mounted 방어 로직", () => {
    it("groups/feeds가 null이면 빈 배열로 대체한다", async () => {
      const wrapper = createWrapper({
        data() {
          return { groups: null, feeds: null };
        },
      });
      await flushPromises();

      expect(Array.isArray(wrapper.vm.feeds)).toBe(true);
    });
  });
});
