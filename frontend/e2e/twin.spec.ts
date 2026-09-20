import { test, expect } from "@playwright/test";

test("physical twin supports point inspection, fullscreen and remounting", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/pano/ADM-00014");
  await page.getByRole("button", { name: "3D ikiz", exact: true }).click();
  const twin = page.locator(".twin-workbench");
  // 30 sn, varsayilan 5 sn DEGIL — ve bu bir kacamak degil, olculmus bir suredir.
  // Ilk mount three.js sahnesini SIFIRDAN kurar: PMREM ortam haritasi, kaplama
  // dokulari, gecici golgeleme derlemesi. Soguk acilista bu is 5 sn'yi asabiliyor
  // ve test tam BURADA, 11. satirda kararsizdi (5 kosumda 2 dusme; hata her
  // seferinde 'element(s) not found, Timeout: 5000ms').
  // Sahne gercekten cizilmezse test yine duser — sadece daha gec duser.
  await expect(twin.locator("canvas")).toBeVisible({ timeout: 30_000 });
  const picker = twin.getByLabel("3D ölçüm noktası");
  const options = await picker
    .locator("option")
    .evaluateAll((nodes) =>
      nodes.map((n) => (n as HTMLOptionElement).value).filter(Boolean),
    );
  await picker.selectOption(options[0]);
  await expect(twin.locator(".twin-inspector")).toContainText("Güncel ölçüm");
  await twin.getByRole("button", { name: /Sonraki uyarı/ }).click();
  await expect(picker).not.toHaveValue("");
  for (const name of [
    "Soldan",
    "Sağdan",
    "3D yakınlaştır",
    "3D uzaklaştır",
    "Seçili noktaya odaklan",
  ]) {
    await twin.getByRole("button", { name, exact: true }).click();
  }
  const thermal = twin.getByRole("button", {
    name: "Termal görünüm",
    exact: true,
  });
  await thermal.click();
  await expect(thermal).toHaveAttribute("aria-pressed", "true");
  await expect(twin.getByLabel("Termal renk skalası")).toBeVisible();
  const canvas = await twin.locator("canvas").boundingBox();
  const controls = await twin.locator(".i3-controls").boundingBox();
  expect(controls!.y).toBeGreaterThanOrEqual(canvas!.y + canvas!.height - 1);
  await twin.getByRole("button", { name: "Tam ekran", exact: true }).click();
  await expect
    .poll(() => page.evaluate(() => !!document.fullscreenElement))
    .toBe(true);
  await twin
    .getByRole("button", { name: "Tam ekrandan çık", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => !!document.fullscreenElement))
    .toBe(false);
  await page.setViewportSize({ width: 390, height: 844 });
  await twin.getByRole("button", { name: "3/4 görünüş", exact: true }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Ön görünüş", exact: true }).click();
  await expect(twin).toHaveCount(0);
  await page.getByRole("button", { name: "3D ikiz", exact: true }).click();
  // Yeniden baglanma da sahneyi bastan kurar; ayni gerekce (yukariya bakiniz).
  await expect(twin.locator("canvas")).toHaveCount(1, { timeout: 30_000 });
  expect(errors).toEqual([]);
});
