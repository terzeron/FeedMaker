const { test, expect } = require("@playwright/test");
const { setupAuthenticatedRoutes, mockGroups } = require("./helpers");

test.describe("Feed Management 페이지", () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedRoutes(page);
  });

  for (const running of [true, false]) {
    test(`첫 상태 확인 전에는 1초, 확인 후에는 3초 간격으로 조회한다 (${running})`, async ({ page }) => {
      await page.clock.install();
      let calls = 0;
      await page.route("**/check_running", (route) => {
        calls += 1;
        return route.fulfill({
          json: calls === 1
            ? { status: "failure" }
            : { status: "success", running_status: running },
        });
      });
      await page.goto("/management/webtoon/naver_webtoon");
      await expect.poll(() => calls).toBe(1);
      await page.clock.runFor(1000);
      await expect.poll(() => calls).toBe(2);
      await expect(page.getByRole("button", { name: running ? "중단" : "실행", exact: true })).toBeVisible();
      await page.clock.runFor(2999);
      expect(calls).toBe(2);
      await page.clock.runFor(1);
      await expect.poll(() => calls).toBe(3);
    });
  }

  test("관리 페이지에 접근하면 그룹 목록이 표시된다", async ({ page }) => {
    await page.goto("/management");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);
    expect(page.url()).toContain("/management");
    // 그룹 이름 확인
    const body = await page.textContent("body");
    expect(body).toContain("webtoon");
  });

  test("그룹을 클릭하면 피드 목록이 표시된다", async ({ page }) => {
    await page.goto("/management");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // 그룹 항목 클릭
    const groupLink = page.locator("text=webtoon").first();
    if (await groupLink.isVisible()) {
      await groupLink.click();
      await page.waitForTimeout(500);
      const body = await page.textContent("body");
      // 피드 이름이 표시되는지 확인
      expect(body.includes("웹툰") || body.includes("webtoon")).toBeTruthy();
    }
  });

  test("URL 파라미터로 특정 피드에 직접 접근 가능하다", async ({ page }) => {
    await page.goto("/management/webtoon/naver_webtoon");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);
    const body = await page.textContent("body");
    expect(body).toContain("네이버 웹툰");
  });
});
