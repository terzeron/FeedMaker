import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import FeedManagement from "../FeedManagement.vue";
import axios from "axios";

const jsonEditorMock = vi.hoisted(() =>
  vi.fn(function JSONEditorMock() {
    this.set = vi.fn();
    this.get = vi.fn().mockReturnValue({});
    this.update = vi.fn();
    this.expandAll = vi.fn();
    this.destroy = vi.fn();
  }),
);

vi.mock("axios");
vi.mock("jsoneditor", () => ({ default: jsonEditorMock }));

const stubs = {
  MyButton: { template: "<button><slot /></button>" },
  "font-awesome-icon": true,
  BAlert: { template: "<div><slot /></div>" },
  BModal: { template: "<div><slot /></div>" },
  BContainer: { template: "<div><slot /></div>" },
  BRow: { template: "<div><slot /></div>" },
  BCol: { template: "<div><slot /></div>" },
  BInputGroup: { template: "<div><slot /></div>" },
  BFormInput: { template: "<input />" },
  BInputGroupText: { template: "<div><slot /></div>" },
  BSpinner: { template: "<span class='spinner' />" },
  BTableSimple: { template: "<table><slot /></table>" },
  BThead: { template: "<thead><slot /></thead>" },
  BTbody: { template: "<tbody><slot /></tbody>" },
  BTr: { template: "<tr><slot /></tr>" },
  BTh: { template: "<th><slot /></th>" },
  BTd: { template: "<td><slot /></td>" },
  BProgress: { template: "<div><slot /></div>" },
  BProgressBar: { template: "<div><slot /></div>" },
};

const TITLE = "나 혼자만 레벨업::네이버웹툰";

const mountWithEditor = async () => {
  axios.get.mockResolvedValueOnce({ data: { status: "success", groups: [] } });
  const wrapper = mount(FeedManagement, {
    global: { stubs, mocks: { $route: { params: {} } } },
  });
  await vi.runAllTimersAsync();
  wrapper.vm.jsonData = {
    rss: {
      title: "기존 제목::사이트",
      link: "https://terzeron.com/old_name.xml",
      description: "",
    },
  };
  wrapper.vm.showEditor = true;
  wrapper.vm.showNewFeedNameInput = true;
  wrapper.vm.feedIsActive = true;
  await nextTick();
  wrapper.vm.initJsonEditor();
  await nextTick();
  const editor = jsonEditorMock.mock.instances.at(-1);
  const options = jsonEditorMock.mock.calls.at(-1)[1];
  // 편집기에서 rss.title을 바꾼 것처럼 onChange를 일으킨다
  const typeTitle = (title) => {
    editor.get.mockReturnValue({ rss: { ...wrapper.vm.jsonData.rss, title } });
    options.onChange();
  };
  return { wrapper, editor, typeTitle };
};

describe("FeedManagement.vue - rss.title 피드명 자동 번역", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("title 입력이 1초 멈춘 뒤에만 한 번 번역하고 피드명을 채운다", async () => {
    const { wrapper, editor, typeTitle } = await mountWithEditor();
    axios.post.mockResolvedValueOnce({
      data: { status: "success", feed_name: "only_i_level_up" },
    });

    typeTitle("나 혼자");
    await vi.advanceTimersByTimeAsync(500);
    typeTitle(TITLE);
    await vi.advanceTimersByTimeAsync(999);
    expect(axios.post).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    expect(axios.post).toHaveBeenCalledTimes(1);
    expect(axios.post.mock.calls[0][0]).toMatch(/\/feed_name_suggestion$/);
    expect(axios.post.mock.calls[0][1]).toEqual({ title: TITLE });

    await vi.runAllTimersAsync();
    expect(wrapper.vm.newFeedName).toBe("only_i_level_up");
    expect(wrapper.vm.jsonData.rss.link).toBe(
      "https://terzeron.com/only_i_level_up.xml",
    );
    expect(editor.update).toHaveBeenCalledWith(wrapper.vm.jsonData);
    expect(wrapper.vm.isTranslatingFeedName).toBe(false);
  });

  it("번역 중에는 spinner를 표시한다", async () => {
    const { wrapper, typeTitle } = await mountWithEditor();
    let resolvePost;
    axios.post.mockReturnValueOnce(new Promise((r) => (resolvePost = r)));

    typeTitle(TITLE);
    await vi.advanceTimersByTimeAsync(1000);
    expect(wrapper.find("[data-testid='feed-name-spinner']").exists()).toBe(
      true,
    );

    resolvePost({ data: { status: "success", feed_name: "only_i_level_up" } });
    await vi.runAllTimersAsync();
    expect(wrapper.find("[data-testid='feed-name-spinner']").exists()).toBe(
      false,
    );
  });

  it("title이 바뀌지 않은 onChange는 번역하지 않는다", async () => {
    const { typeTitle } = await mountWithEditor();

    typeTitle("기존 제목::사이트");
    await vi.runAllTimersAsync();
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("구분자 왼쪽에 한글이 없으면 번역하지 않는다", async () => {
    const { typeTitle } = await mountWithEditor();

    typeTitle("One Piece::네이버웹툰");
    await vi.runAllTimersAsync();
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("번역 중 title이 다시 바뀌면 이전 응답을 버린다", async () => {
    const { wrapper, typeTitle } = await mountWithEditor();
    let resolveFirst;
    axios.post
      .mockReturnValueOnce(new Promise((r) => (resolveFirst = r)))
      .mockResolvedValueOnce({
        data: { status: "success", feed_name: "only_i_level_up" },
      });

    typeTitle("나 혼자::네이버웹툰");
    await vi.advanceTimersByTimeAsync(1000);
    typeTitle(TITLE);
    resolveFirst({ data: { status: "success", feed_name: "me_alone" } });
    await vi.runAllTimersAsync();

    expect(axios.post).toHaveBeenCalledTimes(2);
    expect(wrapper.vm.newFeedName).toBe("only_i_level_up");
  });

  it("번역 실패 시 피드명을 유지하고 알림을 띄운다", async () => {
    const { wrapper, typeTitle } = await mountWithEditor();
    axios.post.mockResolvedValueOnce({
      data: {
        status: "failure",
        message: "ValueError: ANTHROPIC_API_KEY is not set",
      },
    });

    typeTitle(TITLE);
    await vi.runAllTimersAsync();

    expect(wrapper.vm.newFeedName).toBe("old_name");
    expect(wrapper.vm.alertMessage).toContain("ANTHROPIC_API_KEY");
    expect(wrapper.vm.isTranslatingFeedName).toBe(false);
  });
});
