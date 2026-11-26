import type { UserRole } from "@/types";

export interface NavItem {
  label: string;
  to: string;
  roles?: UserRole[];
  permission?: string;
  section?: string;
}

export const platformNavItems: NavItem[] = [
  { label: "Panel", to: "/platform", section: "Plataforma" },
  { label: "Empresas", to: "/platform/companies", permission: "companies.read", section: "Plataforma" },
  { label: "Usuarios", to: "/platform/users", permission: "users.read_global", section: "Plataforma" },
  { label: "Auditoría", to: "/platform/audit", permission: "audit.read_global", section: "Plataforma" },
  { label: "Mi perfil", to: "/app/profile", section: "Cuenta" },
];

export const adminNavItems: NavItem[] = [
  { label: "Panel", to: "/app", section: "General" },
  { label: "Mi perfil", to: "/app/profile", section: "General" },
  { label: "Repositorio", to: "/app/vault", permission: "documents.read", section: "Operaciones" },
  { label: "Licitaciones", to: "/app/tenders", permission: "tenders.read", section: "Operaciones" },
  { label: "Análisis", to: "/app/analysis", permission: "analysis.read", section: "Operaciones" },
  { label: "Chat", to: "/app/chat", permission: "chat.use", section: "Operaciones" },
  { label: "Ofertas", to: "/app/offers", permission: "offers.read", section: "Operaciones" },
  { label: "Configuración de la empresa", to: "/app/settings/company", permission: "company.profile.read", section: "Configuración" },
  { label: "Usuarios", to: "/app/settings/users", permission: "users.read_company", section: "Configuración" },
  { label: "Auditoría", to: "/app/settings/audit", permission: "audit.read_company", section: "Configuración" },
];

export const userNavItems: NavItem[] = [
  { label: "Panel", to: "/app", section: "General" },
  { label: "Mi perfil", to: "/app/profile", section: "General" },
  { label: "Repositorio", to: "/app/vault", permission: "documents.read", section: "Operaciones" },
  { label: "Licitaciones", to: "/app/tenders", permission: "tenders.read", section: "Operaciones" },
  { label: "Análisis", to: "/app/analysis", permission: "analysis.read", section: "Operaciones" },
  { label: "Chat", to: "/app/chat", permission: "chat.use", section: "Operaciones" },
  { label: "Ofertas", to: "/app/offers", permission: "offers.read", section: "Operaciones" },
];
