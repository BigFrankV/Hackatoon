import { expect, type Page } from "@playwright/test";

export interface TestCredentials {
  email: string;
  password: string;
}

export async function login(
  page: Page,
  credentials: TestCredentials,
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Correo electrónico").fill(credentials.email);
  await page.getByLabel("Contraseña").fill(credentials.password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
}

export async function expectForbiddenRoute(
  page: Page,
  path: string,
): Promise<void> {
  await page.goto(path);
  await expect(page).toHaveURL(/\/forbidden(?:\?|$)/);
}
