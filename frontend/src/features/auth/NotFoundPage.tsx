import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth/AuthProvider";

export function NotFoundPage() {
  const { user } = useAuth();
  const home = !user ? "/login" : user.role === "super_admin" ? "/platform" : "/app";
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-sm font-semibold text-slate-500">404</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Página no encontrada</h1>
        <p className="mt-2 text-sm text-slate-600">La página que solicitaste no existe.</p>
        <div className="mt-6 flex justify-center">
          <Link to={home}>
            <Button variant="secondary">Ir al inicio</Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
