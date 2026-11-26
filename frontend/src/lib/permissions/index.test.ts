import { describe, expect, it } from "vitest";

import { hasPermission } from "@/lib/permissions";
import type { UserPublic } from "@/types";

function makeUser(permissions?: string[]): UserPublic {
  return {
    id: "user-1",
    email: "user@example.test",
    first_name: "Test",
    last_name: "User",
    role: "user",
    status: "active",
    company_id: "company-1",
    company: null,
    must_change_password: false,
    last_login_at: null,
    permissions,
  };
}

describe("hasPermission", () => {
  it("uses explicit server grants as the source of truth", () => {
    expect(hasPermission(makeUser([]), "tenders.read")).toBe(false);
    expect(hasPermission(makeUser(["tenders.read"]), "tenders.read")).toBe(true);
  });

  it("uses the role fallback only when server grants are absent", () => {
    expect(hasPermission(makeUser(undefined), "tenders.read")).toBe(true);
  });
});
