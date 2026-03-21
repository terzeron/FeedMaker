const { test, expect } = require("@playwright/test");
const { setupAuthenticatedRoutes } = require("./helpers");

test.describe("실행 결과 페이지", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedRoutes(page);
  });

  test("인증된 사용자는 실행 결과 페이지에 접근 가능하다", async ({ page }) => {
    await page.goto("/result");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/result");
  });

  test("실행 결과 마크다운이 렌더링된다", async ({ page }) => {
    await page.goto("/result");
    await page.waitForLoadState("networkidle");
    // 마크다운 렌더링 대기
    await page.waitForTimeout(500);
    const body = await page.textContent("body");
    expect(body).toContain("FeedMaker");
  });

  test("네비게이션 바가 표시된다", async ({ page }) => {
    await page.goto("/result");
    await page.waitForLoadState("networkidle");
    // navbar에 주요 메뉴 링크 확인
    const nav = page.locator('nav, .navbar, [role="navigation"]');
    await expect(nav.first()).toBeVisible();
  });
});
