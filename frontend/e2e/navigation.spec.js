const { test, expect } = require("@playwright/test");
const {
  setupAuthenticatedRoutes,
  setupUnauthenticatedRoutes,
} = require("./helpers");

test.describe("네비게이션", () => {
  test("인증된 사용자는 각 페이지를 탐색할 수 있다", async ({ page }) => {
    await setupAuthenticatedRoutes(page);

    // 실행 결과 페이지
    await page.goto("/result");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/result");

    // 문제 현황 페이지로 이동
    const problemsLink = page
      .locator(
        'a[href*="problems"], a:has-text("Problems"), a:has-text("문제")',
      )
      .first();
    if (await problemsLink.isVisible()) {
      await problemsLink.click();
      await page.waitForURL("**/problems*");
      expect(page.url()).toContain("/problems");
    }
  });

  test("비인증 사용자는 보호된 페이지에 접근할 수 없다", async ({ page }) => {
    await setupUnauthenticatedRoutes(page);

    await page.goto("/result", { waitUntil: "commit" });
    await page.waitForURL("**/login**", { timeout: 15000 });
    expect(page.url()).toContain("/login");
  });

  test("루트 경로는 /result로 리다이렉트된다", async ({ page }) => {
    await setupAuthenticatedRoutes(page);
    await page.goto("/");
    await page.waitForURL("**/result*");
    expect(page.url()).toContain("/result");
  });
});
