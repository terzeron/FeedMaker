/**
 * E2E 테스트 헬퍼: Playwright page.route()로 API 응답을 intercept
 */

const mockGroups = {
  status: "success",
  groups: [
    { name: "webtoon", num_feeds: 3, is_active: true },
    { name: "news", num_feeds: 2, is_active: true },
    { name: "_disabled", num_feeds: 0, is_active: false },
  ],
};

const mockFeeds = {
  status: "success",
  feeds: [
    {
      name: "naver_webtoon",
      title: "네이버 웹툰",
      group_name: "webtoon",
      is_active: true,
    },
    {
      name: "kakao_webtoon",
      title: "카카오 웹툰",
      group_name: "webtoon",
      is_active: true,
    },
  ],
};

const mockFeedInfo = {
  status: "success",
  feed_info: {
    feed_name: "naver_webtoon",
    feed_title: "네이버 웹툰",
    group_name: "webtoon",
    config: {
      collection: {
        list_url_list: ["https://example.com/list"],
        is_completed: false,
      },
      extraction: { render_js: false },
      rss: {
        title: "네이버 웹툰",
        link: "https://terzeron.com/naver_webtoon.xml",
      },
    },
    collection_info: {
      collect_date: "2025-06-25T03:55:05",
      total_item_count: 7,
    },
    public_feed_info: {
      num_items: 7,
      file_size: 3430,
      upload_date: "2025-06-25T09:34:05",
    },
    progress_info: {
      current_index: 3,
      total_item_count: 16,
      unit_size_per_day: 3,
      progress_ratio: 24.5,
      due_date: "2025-06-28",
    },
  },
};

const mockExecResult = {
  status: "success",
  exec_result:
    "# FeedMaker 실행 결과\n\n| 피드 | 상태 | 처리 수 |\n|------|------|--------|\n| naver_webtoon | 성공 | 15 |\n| kakao_webtoon | 부분 성공 | 7/8 |",
};

const mockProblems = {
  status: "success",
  result: {
    naver_webtoon: {
      feed_name: "naver_webtoon",
      feed_title: "네이버 웹툰",
      group_name: "webtoon",
      http_request: "ok",
      feedmaker: true,
      public_html: true,
    },
  },
};

const mockSearchResult = {
  status: "success",
  feeds: [
    {
      feed_name: "naver_webtoon",
      feed_title: "네이버 웹툰",
      group_name: "webtoon",
      is_active: true,
    },
  ],
};

/**
 * 인증된 상태로 API 라우팅을 설정합니다.
 */
async function setupAuthenticatedRoutes(page) {
  // Auth check - 인증된 사용자로 응답
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        is_authenticated: true,
        email: "test@example.com",
        name: "TestUser",
      }),
    }),
  );

  // Groups
  await page.route("**/groups", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockGroups),
      });
    }
    return route.continue();
  });

  // Feeds by group
  await page.route("**/groups/*/feeds", (route) => {
    if (
      route.request().method() === "GET" &&
      !route.request().url().includes("/feeds/")
    ) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockFeeds),
      });
    }
    return route.continue();
  });

  // Feed info
  await page.route("**/groups/*/feeds/*", (route) => {
    const url = route.request().url();
    if (
      route.request().method() === "GET" &&
      !url.includes("check_running") &&
      !url.includes("htmls") &&
      !url.includes("list") &&
      !url.includes("toggle") &&
      !url.includes("run")
    ) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockFeedInfo),
      });
    }
    if (url.includes("check_running")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "success", running_status: false }),
      });
    }
    if (url.includes("toggle") && route.request().method() === "PUT") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "success", new_name: "_naver_webtoon" }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "success" }),
    });
  });

  // Exec result
  await page.route("**/exec_result", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockExecResult),
    }),
  );

  // Problems
  await page.route("**/problems/*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockProblems),
    }),
  );

  // Search
  await page.route("**/search/*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockSearchResult),
    }),
  );

  // Site config
  await page.route("**/groups/*/site_config", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "success", configuration: {} }),
    }),
  );

  // Toggle group
  await page.route("**/groups/*/toggle", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "success", new_name: "_webtoon" }),
    }),
  );
}

/**
 * 비인증 상태로 API 라우팅을 설정합니다.
 */
async function setupUnauthenticatedRoutes(page) {
  await page.route("**/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ is_authenticated: false }),
    }),
  );
}

module.exports = {
  setupAuthenticatedRoutes,
  setupUnauthenticatedRoutes,
  mockGroups,
  mockFeeds,
  mockFeedInfo,
  mockExecResult,
  mockProblems,
  mockSearchResult,
};
