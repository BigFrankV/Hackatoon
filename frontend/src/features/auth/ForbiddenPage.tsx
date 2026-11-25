import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth/AuthProvider";

export function ForbiddenPage() {
  const { user } = useAuth();
  const home = user?.role === "super_admin" ? "/platform" : "/app";
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold text-red-600">403</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Acceso denegado</h1>
        <p className="mt-2 text-sm text-slate-600">
          No tienes permiso para acceder a esta página.
        </p>
        <div className="mt-6 flex justify-center">
          <Link to={home}>
            <Button variant="secondary">Ir al panel</Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
