import type { UserPublic, UserRole } from "@/types";

export const ROLE_LABELS: Record<UserRole, string> = {
  super_admin: "Superadministrador",
  admin: "Administrador",
  user: "Usuario",
};

export function hasRole(user: UserPublic | null | undefined, roles: UserRole[]): boolean {
  if (!user) return false;
  return roles.includes(user.role);
}

export function hasPermission(
  user: UserPublic | null | undefined,
  permission: string,
): boolean {
  if (!user) return false;
  if (user.permissions?.includes(permission)) return true;

  const rolePermissions: Record<UserRole, string[]> = {
    super_admin: [
      "companies.read",
      "companies.create",
      "companies.update",
      "companies.deactivate",
      "companies.activate",
      "users.read_global",
      "users.create_global",
      "users.update_global",
      "users.deactivate_global",
      "users.activate_global",
      "users.reset_password_global",
      "users.revoke_sessions_global",
      "profile.read_own",
      "profile.update_own",
      "profile.change_password",
      "audit.read_global",
    ],
    admin: [
      "company.profile.read",
      "company.profile.update",
      "users.read_company",
      "users.create_company",
      "users.update_company",
      "users.deactivate_company",
      "users.activate_company",
      "users.reset_password_company",
      "users.revoke_sessions_company",
      "profile.read_own",
      "profile.update_own",
      "profile.change_password",
      "audit.read_company",
    ],
    user: ["profile.read_own", "profile.update_own", "profile.change_password"],
  };

  return rolePermissions[user.role]?.includes(permission) ?? false;
}

export function canAccessPlatform(user: UserPublic | null | undefined): boolean {
  return hasRole(user, ["super_admin"]);
}

export function canAccessApp(user: UserPublic | null | undefined): boolean {
  return hasRole(user, ["admin", "user", "super_admin"]);
}
