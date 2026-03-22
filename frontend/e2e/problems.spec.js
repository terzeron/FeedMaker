const { test, expect } = require("@playwright/test");
const { setupAuthenticatedRoutes } = require("./helpers");

test.describe("Problems 페이지", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedRoutes(page);
  });

  test("문제 현황 페이지에 접근 가능하다", async ({ page }) => {
    await page.goto("/problems");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/problems");
  });

  test("탭 목록이 표시된다", async ({ page }) => {
    await page.goto("/problems");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);
    // 탭 또는 버튼 형태의 problem type 선택 요소 확인
    const tabs = page.locator('[role="tab"], .nav-link, .nav-item a');
    const count = await tabs.count();
    expect(count).toBeGreaterThan(0);
  });

  test("테이블 데이터가 렌더링된다", async ({ page }) => {
    await page.goto("/problems");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);
    // 테이블 또는 데이터 영역 확인
    const table = page.locator('table, .table, [role="table"]');
    const count = await table.count();
    expect(count).toBeGreaterThan(0);
  });
});
