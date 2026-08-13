import { mount } from "@vue/test-utils";
import Problems from "../Problems.vue";
import axios from "axios";

vi.mock("axios");

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

const EMPTY = { data: { status: "success", result: [] } };

// URL별로 응답을 지정한다. 지정하지 않은 엔드포인트는 빈 결과를 돌려준다.
const mountWith = (byPath = {}) => {
  axios.get.mockImplementation((url) => {
    const match = Object.keys(byPath).find((p) => url.includes(p));
    return Promise.resolve(match ? byPath[match] : EMPTY);
  });
  return mount(Problems, { global: { stubs } });
};

describe("Problems.vue - 미커버 분기", () => {
  let warnSpy;
  let alertSpy;

  beforeEach(() => {
    axios.get.mockReset();
    axios.delete.mockReset();
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  afterEach(() => {
    warnSpy.mockRestore();
    alertSpy.mockRestore();
  });

  describe("sorted* computed - 배열이 아닌 원본", () => {
    it("원본 목록이 null이면 빈 배열을 반환한다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        progressInfolist: null,
        listUrlInfolist: null,
        elementInfolist: null,
        htmlFileSizelist: null,
        htmlFileWithoutImageTaglist: null,
        htmlFileWithManyImageTaglist: null,
        htmlFileWithImageNotFoundlist: null,
        publicFeedInfolist: null,
      });

      expect(wrapper.vm.sortedProgressInfolist).toEqual([]);
      expect(wrapper.vm.sortedListUrlInfolist).toEqual([]);
      expect(wrapper.vm.sortedElementInfolist).toEqual([]);
      expect(wrapper.vm.sortedHtmlFileSizelist).toEqual([]);
      expect(wrapper.vm.sortedHtmlFileWithoutImageTaglist).toEqual([]);
      expect(wrapper.vm.sortedHtmlFileWithManyImageTaglist).toEqual([]);
      expect(wrapper.vm.sortedHtmlFileWithImageNotFoundlist).toEqual([]);
      expect(wrapper.vm.sortedPublicFeedInfolist).toEqual([]);
    });
  });

  describe("status_info 삭제", () => {
    it("제목이 비어 있으면 '(제목 없음)'으로 확인 메시지를 만든다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      const message = wrapper.vm.getStatusInfoDeleteMessage({
        group_name: "",
        feed_name: "",
        feed_title: "",
      });

      expect(message).toContain("제목: (제목 없음)");
    });

    it("feed_title이 없으면 payload에서 빈 문자열로 채운다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      const payload = wrapper.vm.buildStatusInfoDeletePayload({
        feedmaker: "O",
      });

      expect(payload).toEqual({
        feed_name: "",
        feed_title: "",
        group_name: "",
        feedmaker: true,
        public_html: false,
        http_request: false,
      });
    });

    it("삭제 응답이 failure면 오류를 alert한다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      const item = { feed_title: "고아 레코드" };
      wrapper.vm.statusInfolist = [item];
      axios.delete.mockResolvedValueOnce({
        data: { status: "failure", message: "DB 오류" },
      });

      wrapper.vm.removeStatusInfoRecord(item);
      await flushPromises();

      expect(alertSpy).toHaveBeenCalledWith(
        "피드 삭제 중에 오류가 발생하였습니다. DB 오류",
      );
      // 실패했으므로 목록에서 제거되지 않는다.
      expect(wrapper.vm.statusInfolist).toHaveLength(1);
    });

    it("삭제 요청이 실패하면 오류를 alert한다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      const item = { feed_title: "고아 레코드" };
      wrapper.vm.statusInfolist = [item];
      axios.delete.mockRejectedValueOnce(new Error("Network Error"));

      wrapper.vm.removeStatusInfoRecord(item);
      await flushPromises();

      expect(alertSpy).toHaveBeenCalledWith(
        expect.stringContaining("피드 삭제 요청 중에 오류가 발생하였습니다."),
      );
      expect(wrapper.vm.statusInfolist).toHaveLength(1);
    });
  });

  describe("테이블 렌더링", () => {
    it("정렬 불가 컬럼('작업') 헤더 클릭은 정렬 상태를 바꾸지 않는다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        statusInfolist: [{ feed_title: "A", feed_name: "a" }],
        htmlFileSizelist: [{ feed_dir_path: "g/a", file_name: "f.html" }],
        htmlFileWithoutImageTaglist: [
          { feed_dir_path: "g/a", file_name: "f.html" },
        ],
        htmlFileWithManyImageTaglist: [
          { feed_dir_path: "g/a", file_name: "f.html", count: 3 },
        ],
        htmlFileWithImageNotFoundlist: [
          { feed_dir_path: "g/a", file_name: "f.html" },
        ],
        publicFeedInfolist: [{ feed_title: "A", feed_name: "a", size: 1 }],
      });

      const before = {
        statusInfo: wrapper.vm.statusInfoSortBy,
        htmlFileSize: wrapper.vm.htmlFileSizeSortBy,
        htmlFileWithoutImageTag: wrapper.vm.htmlFileWithoutImageTagSortBy,
        htmlFileWithManyImageTag: wrapper.vm.htmlFileWithManyImageTagSortBy,
        htmlFileWithImageNotFound: wrapper.vm.htmlFileWithImageNotFoundSortBy,
        publicFeedInfo: wrapper.vm.publicFeedInfoSortBy,
      };

      const actionHeaders = wrapper
        .findAll("th")
        .filter((th) => th.text().includes("작업"));
      // 작업 컬럼을 가진 6개 테이블
      expect(actionHeaders).toHaveLength(6);
      for (const th of actionHeaders) {
        await th.trigger("click");
      }

      for (const [table, sortBy] of Object.entries(before)) {
        expect(wrapper.vm[`${table}SortBy`]).toBe(sortBy);
      }
    });

    it("제목이 비어 있으면 feed_name / 'N/A'로 대체 표시한다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        // 링크는 걸리지만 feed_title이 없음 → {{ item[field.key] || item.feed_name }}
        progressInfolist: [
          {
            group_name: "g",
            feed_name: "progress-feed",
            feed_title: "",
            progress_ratio: 1,
          },
        ],
        listUrlInfolist: [
          { group_name: "g", feed_name: "url-feed", feed_title: "", count: 7 },
        ],
        // count 없음 → 'N/A'
        htmlFileWithManyImageTaglist: [
          { feed_dir_path: "g/a", file_name: "f.html" },
        ],
      });

      expect(wrapper.text()).toContain("progress-feed");
      expect(wrapper.text()).toContain("url-feed");
      expect(wrapper.text()).toContain("N/A");
    });

    it("group_name/feed_name이 없으면 링크 없이 제목만 보여준다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        listUrlInfolist: [{ feed_title: "링크없음", count: 7 }],
      });

      expect(wrapper.text()).toContain("링크없음");
      expect(wrapper.find("a").exists()).toBe(false);
    });
  });

  describe("html_info 정규화", () => {
    it("feed_dir_path와 file_path가 없으면 feed_title/file_name을 채우지 않는다", async () => {
      const wrapper = mountWith({
        "/problems/html_info": {
          data: {
            status: "success",
            result: {
              // feed_dir_path 없음 → split 대신 [] 경로, 파트 수 < 2라 feed_title 미할당
              // file_path 없음 → file_name 미할당
              html_file_size_map: [{ size: 10 }],
              html_file_with_many_image_tag_map: [{ count: 30 }],
              html_file_without_image_tag_map: [{}],
              html_file_image_not_found_map: [{}],
            },
          },
        },
      });
      await flushPromises();

      const all = [
        wrapper.vm.htmlFileSizelist[0],
        wrapper.vm.htmlFileWithManyImageTaglist[0],
        wrapper.vm.htmlFileWithoutImageTaglist[0],
        wrapper.vm.htmlFileWithImageNotFoundlist[0],
      ];

      for (const item of all) {
        expect(item["action"]).toBe("Delete");
        expect(item["feed_title"]).toBeUndefined();
        expect(item["file_name"]).toBeUndefined();
      }
      // feed_dir_path가 없으면 관리 페이지 링크 없이 렌더링된다.
      expect(wrapper.findAll("a")).toHaveLength(0);
    });

    it("feed_dir_path가 'group/feed' 형태가 아니면 링크를 걸지 않는다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        htmlFileSizelist: [
          { feed_dir_path: "onlygroup", feed_title: "제목", file_name: "a" },
        ],
      });

      expect(wrapper.text()).toContain("제목");
      expect(wrapper.find("a").exists()).toBe(false);
    });

    it("feed_dir_path가 'group/feed' 형태이면 관리 페이지로 링크한다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        htmlFileSizelist: [
          { feed_dir_path: "g1/f1", feed_title: "제목", file_name: "a.html" },
        ],
      });

      expect(wrapper.find("a").attributes("href")).toBe("/management/g1/f1");
    });
  });

  // 비관적 삭제: removeHtmlFile이 false를 주면 목록에서 행을 지우지 않고 빠져나온다.
  describe("HTML 파일 삭제 실패 시 행 유지", () => {
    const cases = [
      ["imageWithoutImageTagDeleteClicked", "htmlFileWithoutImageTaglist"],
      ["imageWithManyImageTagDeleteClicked", "htmlFileWithManyImageTaglist"],
      ["imageNotFoundDeleteClicked", "htmlFileWithImageNotFoundlist"],
      ["htmlFileSizeDeleteClicked", "htmlFileSizelist"],
    ];

    it.each(cases)(
      "%s는 삭제 실패 시 행을 남긴다",
      async (handler, listName) => {
        const wrapper = mountWith();
        await flushPromises();

        await wrapper.setData({
          [listName]: [{ file_path: "g/f/html/a.html", file_name: "a.html" }],
        });
        const item = wrapper.vm[listName][0];

        wrapper.vm[handler]({ item });
        axios.delete.mockResolvedValueOnce({
          data: { status: "failure", message: "실패" },
        });
        wrapper.vm.handleConfirmOk();
        await flushPromises();

        expect(wrapper.vm[listName]).toEqual([item]);
        expect(alertSpy).toHaveBeenCalled();
      },
    );

    it.each(cases)(
      "%s는 삭제 성공 시 행을 제거한다",
      async (handler, listName) => {
        const wrapper = mountWith();
        await flushPromises();

        await wrapper.setData({
          [listName]: [{ file_path: "g/f/html/a.html", file_name: "a.html" }],
        });
        const item = wrapper.vm[listName][0];

        wrapper.vm[handler]({ item });
        axios.delete.mockResolvedValueOnce({ data: { status: "success" } });
        wrapper.vm.handleConfirmOk();
        await flushPromises();

        expect(wrapper.vm[listName]).toEqual([]);
      },
    );
  });

  describe("status_info 삭제 성공", () => {
    it("피드 삭제가 성공하면 목록에서 행을 제거한다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        statusInfolist: [{ group_name: "g", feed_name: "f", feed_title: "T" }],
      });
      const item = wrapper.vm.statusInfolist[0];

      wrapper.vm.statusInfoDeleteClicked({ item });
      axios.delete.mockResolvedValueOnce({ data: { status: "success" } });
      wrapper.vm.handleConfirmOk();
      await flushPromises();

      expect(wrapper.vm.statusInfolist).toEqual([]);
    });
  });

  // sorted* computed는 항상 배열을 돌려주므로, 로딩 플레이스홀더(v-else)는
  // computed를 덮어쓴 파생 컴포넌트로만 렌더링 상태를 확인할 수 있다.
  describe("로딩 플레이스홀더", () => {
    it("정렬된 목록이 배열이 아니면 모든 표에 '데이터를 불러오는 중...'을 보여준다", async () => {
      const nullComputed = Object.fromEntries(
        Object.keys(Problems.computed)
          .filter((key) => key.startsWith("sorted"))
          .map((key) => [key, () => null]),
      );
      const LoadingProblems = {
        ...Problems,
        computed: { ...Problems.computed, ...nullComputed },
      };

      axios.get.mockResolvedValue({ data: { status: "success", result: [] } });
      const wrapper = mount(LoadingProblems, { global: { stubs } });
      await flushPromises();

      const placeholders = wrapper.findAll("p.text-muted");
      expect(placeholders).toHaveLength(9);
      expect(placeholders[0].text()).toBe("데이터를 불러오는 중...");
      expect(wrapper.find("table").exists()).toBe(false);
    });
  });

  // 이 세 표는 기본 필드가 모두 sortable이라, 정렬 불가 컬럼 클릭 분기는
  // 필드 정의에 sortable:false 컬럼을 추가해야 확인할 수 있다.
  describe("정렬 불가 컬럼 클릭", () => {
    const cases = [
      ["progressInfoFields", "progressInfoSortBy", "progress_ratio", "비정렬P"],
      ["listUrlInfoFields", "listUrlInfoSortBy", "count", "비정렬L"],
      ["elementInfoFields", "elementInfoSortBy", "count", "비정렬E"],
    ];

    it.each(cases)(
      "%s의 sortable:false 컬럼은 클릭해도 정렬 기준이 바뀌지 않는다",
      async (fieldsName, sortByName, defaultSortBy, label) => {
        const wrapper = mountWith();
        await flushPromises();

        await wrapper.setData({
          [fieldsName]: [
            ...wrapper.vm[fieldsName],
            { key: "noop", label, sortable: false },
          ],
        });

        const th = wrapper
          .findAll("th")
          .find((node) => node.text().includes(label));
        expect(th).toBeTruthy();
        await th.trigger("click");

        expect(wrapper.vm[sortByName]).toBe(defaultSortBy);
      },
    );
  });

  describe("퍼블릭 피드 표의 그 외 컬럼", () => {
    it("전용 렌더링이 없는 컬럼은 값을 그대로 출력한다", async () => {
      const wrapper = mountWith();
      await flushPromises();

      await wrapper.setData({
        publicFeedInfoFields: [
          ...wrapper.vm.publicFeedInfoFields,
          { key: "etc", label: "기타", sortable: true },
        ],
        publicFeedInfolist: [
          { feed_name: "f", feed_title: "T", size: 1, etc: "기타값" },
        ],
      });

      expect(wrapper.text()).toContain("기타값");
    });
  });
});
