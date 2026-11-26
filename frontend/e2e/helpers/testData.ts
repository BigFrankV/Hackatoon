import { randomUUID } from "node:crypto";

export function createIsolatedTenantData() {
  const suffix = randomUUID();
  const marker = `e2e-${suffix}`;

  return {
    marker,
    company: {
      legal_name: `E2E ${marker} SpA`,
      display_name: marker,
      email: `company-${suffix}@example.test`,
    },
    admin: {
      email: `admin-${suffix}@example.test`,
      first_name: "E2E",
      last_name: "Admin",
      password: `E2e-${suffix}!`,
    },
  };
}
