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

  // 비관적 삭제 계약: 서버가 성공을 확인해 준 뒤에만 행이 사라진다.
  test("피드 삭제를 확인하면 삭제 요청 후 행이 사라진다", async ({ page }) => {
    const deleteUrls = [];
    await page.route("**/groups/*/feeds/*", (route) => {
      if (route.request().method() !== "DELETE") {
        return route.fallback();
      }
      deleteUrls.push(route.request().url());
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "success" }),
      });
    });

    await page.goto("/problems");
    await page.waitForLoadState("networkidle");

    const deleteButton = page.locator('button[title="피드 삭제"]');
    await expect(deleteButton).toHaveCount(1);
    await deleteButton.click();

    await expect(page.getByText("정말로 실행하시겠습니까?")).toBeVisible();
    await page.getByRole("button", { name: "확인", exact: true }).click();

    await expect(deleteButton).toHaveCount(0);
    expect(deleteUrls).toHaveLength(1);
    // 고아 피드까지 지우기 위해 force=true로 요청한다.
    expect(deleteUrls[0]).toContain("/groups/webtoon/feeds/naver_webtoon");
    expect(deleteUrls[0]).toContain("force=true");
  });

  test("피드 삭제를 취소하면 요청 없이 행이 남는다", async ({ page }) => {
    const deleteUrls = [];
    await page.route("**/groups/*/feeds/*", (route) => {
      if (route.request().method() !== "DELETE") {
        return route.fallback();
      }
      deleteUrls.push(route.request().url());
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "success" }),
      });
    });

    await page.goto("/problems");
    await page.waitForLoadState("networkidle");

    const deleteButton = page.locator('button[title="피드 삭제"]');
    await expect(deleteButton).toHaveCount(1);
    await deleteButton.click();

    await page.getByRole("button", { name: "취소", exact: true }).click();

    await expect(deleteButton).toHaveCount(1);
    expect(deleteUrls).toHaveLength(0);
  });
});
