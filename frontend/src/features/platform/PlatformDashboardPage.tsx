import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { PageLoader } from "@/components/ui/PageLoader";
import { listGlobalAuditLogs } from "@/lib/api/audit";
import { listCompanies } from "@/lib/api/companies";
import { listGlobalUsers } from "@/lib/api/users";
import { formatDateTime } from "@/lib/format";

export function PlatformDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    companies: 0,
    activeCompanies: 0,
    suspendedCompanies: 0,
    users: 0,
  });
  const [recentAudit, setRecentAudit] = useState<
    Array<{ id: string; action: string; entity_type: string; occurred_at: string }>
  >([]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [companies, activeCompanies, suspendedCompanies, users, audit] = await Promise.all([
          listCompanies({ page: 1, page_size: 1 }),
          listCompanies({ page: 1, page_size: 1, status: "active" }),
          listCompanies({ page: 1, page_size: 1, status: "suspended" }),
          listGlobalUsers({ page: 1, page_size: 1 }),
          listGlobalAuditLogs({ page: 1, page_size: 5 }),
        ]);
        if (!mounted) return;
        setStats({
          companies: companies.total,
          activeCompanies: activeCompanies.total,
          suspendedCompanies: suspendedCompanies.total,
          users: users.total,
        });
        setRecentAudit(
          audit.items.map((i) => ({
            id: i.id,
            action: i.action,
            entity_type: i.entity_type,
            occurred_at: i.occurred_at,
          })),
        );
      } catch {
        if (mounted) setError("No se pudieron cargar los datos del panel de la plataforma.");
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
        <h1 className="text-2xl font-semibold text-slate-900">Panel de la plataforma</h1>
        <p className="mt-1 text-sm text-slate-600">
          Resumen global para los administradores de la plataforma.
        </p>
      </div>

      {error ? <Alert variant="error">{error}</Alert> : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total de empresas" value={stats.companies} to="/platform/companies" />
        <StatCard label="Empresas activas" value={stats.activeCompanies} to="/platform/companies?status=active" />
        <StatCard label="Empresas suspendidas" value={stats.suspendedCompanies} to="/platform/companies?status=suspended" />
        <StatCard label="Total de usuarios" value={stats.users} to="/platform/users" />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Actividad reciente de auditoría</h2>
          <Link to="/platform/audit" className="text-sm font-medium text-slate-700 hover:text-slate-900">
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
                    Aún no hay actividad de auditoría.
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

function StatCard({ label, value, to }: { label: string; value: number; to: string }) {
  return (
    <Link
      to={to}
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300"
    >
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
    </Link>
  );
}
