import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { PageLoader } from "@/components/ui/PageLoader";
import { listCompanyAuditLogs } from "@/lib/api/audit";
import { getCompanyProfile, listCompanyUsers } from "@/lib/api/company";
import { useAuth } from "@/lib/auth/AuthProvider";
import { formatDateTime } from "@/lib/format";

export function DashboardPage() {
  const { user } = useAuth();

  if (!user) return null;
  if (user.role === "super_admin") {
    return <Navigate to="/platform" replace />;
  }
  if (user.role === "admin") {
    return <AdminDashboard />;
  }
  return <UserDashboard />;
}

function StatCard({ label, value, to }: { label: string; value: string | number; to?: string }) {
  const content = (
    <>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
    </>
  );
  const className =
    "rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300";
  if (to) {
    return (
      <Link to={to} className={className}>
        {content}
      </Link>
    );
  }
  return <div className={className}>{content}</div>;
}

function AdminDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string>("tu empresa");
  const [usersTotal, setUsersTotal] = useState(0);
  const [recentAudit, setRecentAudit] = useState<
    Array<{ id: string; action: string; entity_type: string; occurred_at: string }>
  >([]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [profile, users, audit] = await Promise.all([
          getCompanyProfile(),
          listCompanyUsers({ page: 1, page_size: 1 }),
          listCompanyAuditLogs({ page: 1, page_size: 5 }),
        ]);
        if (!mounted) return;
        setCompanyName(profile.display_name || profile.legal_name || "tu empresa");
        setUsersTotal(users.total);
        setRecentAudit(
          audit.items.map((i) => ({
            id: i.id,
            action: i.action,
            entity_type: i.entity_type,
            occurred_at: i.occurred_at,
          })),
        );
      } catch {
        if (mounted) setError("No se pudieron cargar los datos del panel de administración.");
      } finally {
        if (mounted) setLoading(false);
      }
    };
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Panel de administración</h1>
        <p className="mt-1 text-sm text-slate-600">
          Resumen operativo de {companyName}.
        </p>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard label="Usuarios de la empresa" value={usersTotal} to="/app/settings/users" />
        <StatCard label="Configuración de la empresa" value="Gestionar" to="/app/settings/company" />
        <StatCard label="Registros de auditoría" value="Revisar" to="/app/settings/audit" />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Actividad reciente de la empresa</h2>
          <Link
            to="/app/settings/audit"
            className="text-sm font-medium text-slate-700 hover:text-slate-900"
          >
            Ver todo
          </Link>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="py-2 pr-4 font-medium">Acción</th>
                <th className="py-2 pr-4 font-medium">Entidad</th>
                <th className="py-2 font-medium">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {recentAudit.length === 0 ? (
                <tr>
                  <td className="py-4 text-slate-500" colSpan={3}>
                    No hay actividad reciente.
                  </td>
                </tr>
              ) : (
                recentAudit.map((item) => (
                  <tr key={item.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-4 text-slate-900">{item.action}</td>
                    <td className="py-2 pr-4 text-slate-600">{item.entity_type}</td>
                    <td className="py-2 text-slate-600">{formatDateTime(item.occurred_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function UserDashboard() {
  const { user } = useAuth();
  const companyName = user?.company?.display_name || user?.company?.legal_name || "tu empresa";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Espacio de trabajo</h1>
        <p className="mt-1 text-sm text-slate-600">
          Bienvenido a {companyName}. Usa la navegación para acceder a tus módulos operativos.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <QuickLink title="Repositorio" description="Gestiona los documentos y las evidencias de la empresa." to="/app/vault" />
        <QuickLink title="Licitaciones" description="Realiza un seguimiento de las oportunidades de licitación y gestiónalas." to="/app/tenders" />
        <QuickLink title="Análisis" description="Consulta los resultados del análisis de licitaciones." to="/app/analysis" />
        <QuickLink title="Chat" description="Colabora con flujos de trabajo asistidos por IA." to="/app/chat" />
        <QuickLink title="Ofertas" description="Prepara y revisa ofertas." to="/app/offers" />
        <QuickLink title="Mi perfil" description="Actualiza tus datos personales y tu contraseña." to="/app/profile" />
      </div>
    </div>
  );
}

function QuickLink({ title, description, to }: { title: string; description: string; to: string }) {
  return (
    <Link
      to={to}
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300"
    >
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      <p className="mt-2 text-sm text-slate-600">{description}</p>
    </Link>
  );
}
