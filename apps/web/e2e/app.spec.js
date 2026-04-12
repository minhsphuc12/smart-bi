const { test, expect } = require("@playwright/test");

test.describe("Smart BI MVP", () => {
  test("home shows welcome and navigation", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Welcome to Smart BI/i })).toBeVisible();
    await expect(page.getByRole("banner").getByRole("link", { name: "Sign in" })).toBeVisible();
    await expect(page.getByRole("navigation").getByRole("link", { name: "Ask Data" })).toBeVisible();
  });

  test("login as admin redirects home and exposes Admin link", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Sign in/i })).toBeVisible();
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("playwright");
    await page.getByRole("button", { name: /Continue/i }).click();
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: /Welcome to Smart BI/i })).toBeVisible();
    await expect(page.getByRole("navigation").getByRole("link", { name: "Admin" })).toBeVisible();
  });

  test("admin console tabs and connections form", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").fill("x");
    await page.getByRole("button", { name: /Continue/i }).click();
    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: /Admin console/i })).toBeVisible();
    await expect(page.getByRole("button", { name: "Connections" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Semantic layer" })).toBeVisible();
    await expect(page.getByRole("button", { name: "AI routing" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /New connection/i })).toBeVisible();
    await expect(page.getByLabel("Source type")).toBeVisible();
    await page.getByRole("button", { name: "Semantic layer" }).click();
    await expect(page.getByRole("heading", { name: "Table dictionary" })).toBeVisible();
  });

  test("ask data: submit only with a configured datasource", async ({ page }) => {
    await page.goto("/ask");
    await expect(page.getByRole("heading", { name: "Ask Data" })).toBeVisible();
    await page.locator("#q").fill("Revenue by day last week?");
    const askBtn = page.getByRole("button", { name: "Ask" });
    if (await askBtn.isDisabled()) {
      await expect(page.getByLabel("Connection")).toBeVisible();
      return;
    }
    await askBtn.click();
    await expect(
      page.getByText("Answer", { exact: true }).first().or(page.getByRole("alert"))
    ).toBeVisible({ timeout: 15_000 });
  });

  test("dashboards list loads", async ({ page }) => {
    await page.goto("/dashboards");
    await expect(page.getByRole("heading", { name: "Dashboards" })).toBeVisible();
    await expect(page.getByRole("button", { name: "New dashboard" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Refresh list" })).toBeVisible();
  });
});
