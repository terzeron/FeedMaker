const { test, expect } = require("@playwright/test");
const { setupAuthenticatedRoutes } = require("./helpers");

const longTitle = "아주아주긴아이템제목".repeat(12);

test.describe("Problems HTML 테이블 아이템 컬럼", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1000 });
    await setupAuthenticatedRoutes(page);
    await page.route("**/problems/html_info", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          result: {
            html_file_size_map: [
              { feed_title: "피드제목".repeat(10), feed_dir_path: "g/a", file_path: "g/a/html/a.html", file_name: "a/html/abc1234.html", size: 10, item_title: longTitle, item_url: "https://example.com/a" },
            ],
            html_file_with_many_image_tag_map: [],
            html_file_without_image_tag_map: [],
            html_file_image_not_found_map: [
              { feed_title: "피드제목".repeat(10), feed_dir_path: "g/b", file_path: "g/b/html/b.html", file_name: "b/html/def5678.html", item_title: longTitle, item_url: "https://example.com/b" },
            ],
          },
        }),
      }),
    );
  });

  for (const header of ["작은 HTML 파일", "이미지 없는 HTML 파일"]) {
    test(`${header}: 아이템 말줄임과 작업 컬럼 노출`, async ({ page }) => {
      await page.goto("/problems");
      const card = page.locator(".col-lg-4").filter({ has: page.getByText(header, { exact: true }) });
      const table = card.locator("table");
      await expect(table.locator("a", { hasText: "아주아주" })).toBeVisible();

      const m = await table.evaluate((t) => {
        const wrap = t.parentElement.getBoundingClientRect();
        const ths = [...t.querySelectorAll("thead th")];
        const action = ths[ths.length - 1].getBoundingClientRect();
        const link = t.querySelector('a[href^="https://example.com"]');
        return {
          tableW: t.getBoundingClientRect().width, wrapW: wrap.width,
          actionRight: action.right, wrapRight: wrap.right,
          linkClip: link.scrollWidth > link.clientWidth,
          layout: getComputedStyle(t).tableLayout,
          linkStyle: (({ display, overflow, textOverflow, whiteSpace }) => ({ display, overflow, textOverflow, whiteSpace }))(getComputedStyle(link)),
          spanStyle: (({ display, maxWidth, overflow }) => ({ display, maxWidth, overflow }))(getComputedStyle(link.parentElement)),
        };
      });
      console.log(header, JSON.stringify(m));
      expect(m.actionRight).toBeLessThanOrEqual(m.wrapRight + 1);
      expect(m.linkClip).toBe(true);
    });
  }
});
