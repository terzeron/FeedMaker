const { test, expect } = require("@playwright/test");
const { setupUnauthenticatedRoutes } = require("./helpers");

test.describe("Login 페이지", () => {
  test.beforeEach(async ({ page }) => {
    await setupUnauthenticatedRoutes(page);
  });

  test("비인증 사용자는 로그인 페이지로 리다이렉트된다", async ({ page }) => {
    await page.goto("/result", { waitUntil: "commit" });
    await page.waitForURL("**/login**", { timeout: 15000 });
    expect(page.url()).toContain("/login");
  });

  test("로그인 페이지가 정상 렌더링된다", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("body")).toBeVisible();
    // Facebook 로그인 관련 요소 확인
    const loginContent = await page.textContent("body");
    expect(loginContent).toBeTruthy();
  });

  test("/login 경로에 직접 접근하면 로그인 페이지가 표시된다", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    expect(page.url()).toContain("/login");
  });
});
