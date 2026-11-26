import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { PlatformLayout } from "@/components/layout/PlatformLayout";
import {
  PublicOnly,
  RequireAuth,
  RequirePermission,
  RequireRoles,
} from "@/app/router/guards";
import { ForbiddenPage } from "@/features/auth/ForbiddenPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { NotFoundPage } from "@/features/auth/NotFoundPage";
import { CompanyAuditPage } from "@/features/company/CompanyAuditPage";
import { CompanySettingsPage } from "@/features/company/CompanySettingsPage";
import { CompanyUserCreatePage } from "@/features/company/CompanyUserCreatePage";
import { CompanyUserDetailPage } from "@/features/company/CompanyUserDetailPage";
import { CompanyUsersPage } from "@/features/company/CompanyUsersPage";
import { ChatPage } from "@/features/chat/ChatPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { VaultPage } from "@/features/documents/VaultPage";
import { ModulePlaceholderPage } from "@/features/placeholders/ModulePlaceholderPage";
import { CompaniesPage } from "@/features/platform/CompaniesPage";
import { CompanyCreatePage } from "@/features/platform/CompanyCreatePage";
import { CompanyDetailPage } from "@/features/platform/CompanyDetailPage";
import { PlatformAuditPage } from "@/features/platform/PlatformAuditPage";
import { PlatformDashboardPage } from "@/features/platform/PlatformDashboardPage";
import { PlatformUserCreatePage } from "@/features/platform/PlatformUserCreatePage";
import { PlatformUserDetailPage } from "@/features/platform/PlatformUserDetailPage";
import { PlatformUsersPage } from "@/features/platform/PlatformUsersPage";
import { ProfilePage } from "@/features/profile/ProfilePage";

function Placeholder({ title, description }: { title: string; description: string }) {
  return <ModulePlaceholderPage title={title} description={description} />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicOnly>
            <LoginPage />
          </PublicOnly>
        }
      />
      <Route path="/forbidden" element={<ForbiddenPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<RequireRoles roles={["super_admin"]} />}>
          <Route path="/platform" element={<PlatformLayout />}>
            <Route index element={<PlatformDashboardPage />} />
            <Route path="companies" element={<CompaniesPage />} />
            <Route path="companies/new" element={<CompanyCreatePage />} />
            <Route path="companies/:companyId" element={<CompanyDetailPage />} />
            <Route path="users" element={<PlatformUsersPage />} />
            <Route path="users/new" element={<PlatformUserCreatePage />} />
            <Route path="users/:userId" element={<PlatformUserDetailPage />} />
            <Route path="audit" element={<PlatformAuditPage />} />
          </Route>
        </Route>

        <Route path="/app" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="profile" element={<ProfilePage />} />

          <Route element={<RequireRoles roles={["admin", "user"]} />}>
            <Route element={<RequirePermission permission="documents.read" />}>
              <Route
                path="vault"
                element={<VaultPage />}
              />
            </Route>
            <Route element={<RequirePermission permission="tenders.read" />}>
              <Route
                path="tenders"
                element={
                  <Placeholder
                    title="Licitaciones"
                    description="Búsqueda y seguimiento de licitaciones."
                  />
                }
              />
              <Route
                path="tenders/:tenderId"
                element={
                  <Placeholder
                    title="Detalle de la licitación"
                    description="Detalle y gestión del ciclo de vida de la licitación."
                  />
                }
              />
            </Route>
            <Route element={<RequirePermission permission="tenders.manage" />}>
              <Route
                path="tenders/new"
                element={
                  <Placeholder
                    title="Nueva licitación"
                    description="Flujo de creación de licitaciones."
                  />
                }
              />
            </Route>
            <Route element={<RequirePermission permission="analysis.read" />}>
              <Route
                path="analysis"
                element={
                  <Placeholder
                    title="Análisis"
                    description="Análisis de licitaciones y documentos."
                  />
                }
              />
            </Route>
            <Route element={<RequirePermission permission="chat.use" />}>
              <Route
                path="chat"
                element={<ChatPage />}
              />
            </Route>
            <Route element={<RequirePermission permission="offers.read" />}>
              <Route
                path="offers"
                element={
                  <Placeholder
                    title="Ofertas"
                    description="Preparación y revisión de ofertas."
                  />
                }
              />
            </Route>
          </Route>

          <Route element={<RequireRoles roles={["admin"]} />}>
            <Route path="settings" element={<Navigate to="/app/settings/company" replace />} />
            <Route path="settings/company" element={<CompanySettingsPage />} />
            <Route path="settings/users" element={<CompanyUsersPage />} />
            <Route path="settings/users/new" element={<CompanyUserCreatePage />} />
            <Route path="settings/users/:userId" element={<CompanyUserDetailPage />} />
            <Route path="settings/audit" element={<CompanyAuditPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
