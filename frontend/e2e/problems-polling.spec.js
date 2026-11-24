const { test, expect } = require("@playwright/test");
const { setupAuthenticatedRoutes } = require("./helpers");

test("진행 현황을 깜빡임 없이 갱신하고 실행 중인 제목만 강조한다", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await setupAuthenticatedRoutes(page);
  await page.clock.install();
  let requests = 0;
  let releaseRefresh;
  const makeFeed = (name, running, count) => ({
    group_name: "webtoon", feed_name: name, feed_title: name,
    running_status: running, progress_ratio: count,
    html_file_count: count, total_item_count: 100,
  });
  await page.route("**/problems/progress_info", async (route) => {
    requests += 1;
    const currentRequest = requests;
    if (currentRequest === 2) {
      await new Promise((resolve) => { releaseRefresh = resolve; });
    }
    await route.fulfill({ json: {
      status: "success",
      result: currentRequest === 1
        ? [makeFeed("active", true, 20), makeFeed("idle", false, 10)]
        : [makeFeed("active", false, 5), makeFeed("idle", true, 30)],
    } });
  });

  await page.goto("/problems");
  const table = page.locator("table").nth(1);
  const activeTitle = table.getByRole("cell").filter({ hasText: "active" });
  const idleTitle = table.getByRole("cell").filter({ hasText: "idle" });
  await expect(activeTitle).toHaveCSS("background-color", "rgb(255, 255, 128)");
  await expect(activeTitle).toHaveCSS("box-shadow", "none");
  await expect(idleTitle).not.toHaveClass(/progress-running-title/);
  const originalTitle = await activeTitle.elementHandle();
  await page.screenshot({ path: "/tmp/fm-problems-polling-before.png" });

  await page.clock.runFor(10000);
  await expect.poll(() => requests).toBe(2);
  await expect(table.locator("tbody tr")).toHaveCount(2);
  await expect(table).toContainText("20 / 100");
  await expect(activeTitle).toHaveCSS("background-color", "rgb(255, 255, 128)");
  releaseRefresh();

  await expect(table).toContainText("30 / 100");
  await expect(activeTitle).not.toHaveClass(/progress-running-title/);
  await expect(idleTitle).toHaveCSS("background-color", "rgb(255, 255, 128)");
  expect(await originalTitle.evaluate((element) => element.isConnected)).toBe(true);
  await page.screenshot({ path: "/tmp/fm-problems-polling-after.png" });
  expect(errors).toEqual([]);

  await page.getByRole("link", { name: "피드 관리", exact: true }).click();
  await page.clock.runFor(30000);
  expect(requests).toBe(2);
});
