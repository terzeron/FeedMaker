const { test, expect } = require("@playwright/test");
const { setupAuthenticatedRoutes, mockFeedInfo } = require("./helpers");

test("HTML 개수와 newlist 개수를 구분해서 표시한다", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await setupAuthenticatedRoutes(page);
  const progress = {
    feed_title: "네이버 웹툰", group_name: "webtoon", feed_name: "naver_webtoon",
    current_index: 3, html_file_count: 8, total_item_count: 20,
    unit_size_per_day: 1, progress_ratio: 15, due_date: "2026-11-20",
  };
  await page.route("**/problems/progress_info", (route) => route.fulfill({
    json: { status: "success", result: [progress] },
  }));
  await page.goto("/problems");
  const card = page.locator("table").nth(1);
  await expect(card.locator("tbody tr").first().locator("td").nth(2)).toHaveText("8");
  await page.screenshot({ path: "/tmp/fm-problems-count.png" });

  await page.route("**/groups/webtoon/feeds/naver_webtoon", (route) => route.fulfill({
    json: {
      ...mockFeedInfo,
      feed_info: { ...mockFeedInfo.feed_info, progress_info: progress },
    },
  }));
  await page.goto("/management/webtoon/naver_webtoon");
  await expect(page.locator("#metadata")).toContainText("3 / 8 / 20 = 15 %");
  await page.screenshot({ path: "/tmp/fm-management-count.png" });
  expect(errors).toEqual([]);
});
