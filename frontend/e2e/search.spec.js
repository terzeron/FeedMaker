const { test, expect } = require("@playwright/test");
const { setupAuthenticatedRoutes } = require("./helpers");

test.describe("Search 페이지", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedRoutes(page);
  });

  test("검색 페이지에 접근 가능하다", async ({ page }) => {
    await page.goto("/search");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/search");
  });

  test("검색 입력창이 표시된다", async ({ page }) => {
    await page.goto("/search");
    await page.waitForLoadState("networkidle");
    const input = page.locator(
      'input[type="text"], input[type="search"], input[placeholder]',
    );
    await expect(input.first()).toBeVisible();
  });

  test("키워드를 입력하고 검색 버튼/엔터를 누르면 API가 호출된다", async ({
    page,
  }) => {
    let searchCalled = false;
    // search_sites 이름 목록 API
    await page.route("**/search_sites", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "success", site_names: ["testsite"] }),
      }),
    );
    // 사이트별 검색 API
    await page.route("**/search_sites/**", (route) => {
      searchCalled = true;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          search_result: "<div>결과</div>",
        }),
      });
    });

    await page.goto("/search");
    await page.waitForLoadState("networkidle");

    const input = page
      .locator('input[type="text"], input[type="search"], input[placeholder]')
      .first();
    await input.fill("webtoon");
    await input.press("Enter");
    await page.waitForTimeout(2000);
    // 검색 API가 호출되었는지 확인
    expect(searchCalled).toBe(true);
  });
});
