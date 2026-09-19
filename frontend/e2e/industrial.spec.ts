import { test, expect } from "@playwright/test";

test("measurement controls, keyboard data access, export and panel routing", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/trend/ADM-00014");
  await expect(page.locator(".instrument-chart svg")).toHaveCount(4);
  const k = page.locator(".instrument-chart").nth(1);
  const legend = k.getByRole("button", { name: "K/K₀", exact: true });
  await legend.click();
  await expect(legend).toHaveAttribute("aria-pressed", "false");
  await legend.click();
  await expect(legend).toHaveAttribute("aria-pressed", "true");
  await k.locator("summary").click();
  const slider = k.getByRole("slider");
  await slider.focus();
  await slider.press("End");
  await expect(slider).toHaveValue((await slider.getAttribute("max")) ?? "");
  const downloaded = page.waitForEvent("download");
  await k.getByRole("button", { name: /SVG indir/ }).click();
  expect((await downloaded).suggestedFilename()).toBe("pano-analiz.svg");
  await page.getByRole("button", { name: "Son 7 gün", exact: true }).click();
  await expect(k.locator("summary")).toContainText("169 zaman noktası");
  await page.locator("#pano-select").selectOption("GDZ-00231");
  await expect(page).toHaveURL(/trend\/GDZ-00231/);
  await expect(page.locator(".instrument-chart svg")).toHaveCount(4);
  expect(errors).toEqual([]);
});

test("3D evidence loads on demand and supports view controls", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/trend/ADM-00014");
  await expect(page.locator(".instrument-chart svg")).toHaveCount(4);
  await page
    .getByRole("button", { name: "3D ölçüm uzayı", exact: true })
    .click();
  await expect(page.locator(".spatial-host canvas").first()).toBeVisible({
    timeout: 30000,
  });
  await expect(page.locator(".spatial-chart [role=alert]")).toHaveCount(0);
  await page.getByRole("button", { name: "Önden", exact: true }).click();
  await page.getByRole("button", { name: "Görünümü sıfırla" }).click();
  await page.locator(".spatial-chart summary").click();
  await expect(page.locator(".spatial-chart tbody tr")).toHaveCount(337);
  await page.getByRole("button", { name: "2D analiz", exact: true }).click();
  await expect(page.locator(".spatial-chart")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("light chart palette, aligned controls and orange alarm selections", async ({
  page,
}) => {
  await page.goto("/trend/ADM-00014");
  await expect(page.locator(".instrument-chart svg")).toHaveCount(4);
  await expect(page.locator(".instrument-chart").first()).toHaveCSS(
    "background-color",
    "rgb(255, 255, 255)",
  );
  const select = await page.locator("#pano-select").boundingBox();
  const period = await page
    .locator(".console-filters .chart-range")
    .boundingBox();
  expect(
    Math.abs(select!.y + select!.height - period!.y - period!.height),
  ).toBeLessThan(2);
  await page
    .getByRole("button", { name: "3D ölçüm uzayı", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Isıl yüzey · model", exact: true })
    .click();
  await expect(page.locator(".spatial-host canvas").first()).toBeVisible();
  await expect(page.locator(".surface-explanation")).toContainText(
    "her kesişim ölçülmüş değildir",
  );
  await expect(page.locator(".spatial-chart [role=alert]")).toHaveCount(0);
  await page.goto("/alarmlar");
  const shelf = page.getByRole("button", { name: "Rafta", exact: true });
  await shelf.click();
  await expect(shelf).toHaveCSS("background-color", "rgb(255, 103, 30)");
});

test("WebGL unavailable keeps measured table available", async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      ...args: Parameters<typeof original>
    ) {
      if (String(args[0]).includes("webgl")) return null;
      return original.apply(this, args);
    } as typeof original;
  });
  await page.goto("/trend/ADM-00014");
  await expect(page.locator(".instrument-chart svg")).toHaveCount(4);
  await page
    .getByRole("button", { name: "3D ölçüm uzayı", exact: true })
    .click();
  await expect(page.locator(".spatial-chart [role=alert]")).toContainText(
    "bu cihazda açılamadı",
  );
  await page.locator(".spatial-chart summary").click();
  await expect(page.locator(".spatial-chart tbody tr")).toHaveCount(337);
});

test("event investigation charts remain available in the printed report", async ({
  page,
}) => {
  await page.goto("/olay");
  await page.locator('a[href="/olay/EVT-42"]').click();
  await expect(page.locator(".instrument-chart svg").first()).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".instrument-tools").first()).toBeHidden();
  await expect(page.locator(".instrument-chart svg").first()).toBeVisible();
  await expect(page.locator(".print-sign")).toBeVisible();
  await expect(page.locator(".sidebar")).toBeHidden();
  await expect(page.locator(".workspace-topbar")).toBeHidden();
});

for (const width of [1440, 390]) {
  test(`workspace routes at ${width}px have no page overflow or crashes`, async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.setViewportSize({ width, height: 1000 });
    for (const route of [
      "/",
      "/alarmlar",
      "/bolge",
      "/trend/ADM-00014",
      "/olay",
      "/cihaz-sagligi",
      "/pano/ADM-00014",
    ]) {
      await page.goto(route);
      await expect(page.locator("main h1")).toBeVisible();
      await page.waitForTimeout(600);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        route,
      ).toBe(true);
    }
    expect(errors).toEqual([]);
  });
}
