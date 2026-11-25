import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiRequestError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { UserPublic } from "@/types";

function defaultRouteForUser(user: UserPublic): string {
  return user.role === "super_admin" ? "/platform" : "/app";
}

export function LoginPage() {
  const { login, authError, clearAuthError, status, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || null;

  useEffect(() => {
    if (status === "authenticated" && user) {
      navigate(defaultRouteForUser(user), { replace: true });
    }
  }, [status, user, navigate]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    clearAuthError();

    if (!email.trim() || !password) {
      setError("El correo electrónico y la contraseña son obligatorios.");
      return;
    }

    setSubmitting(true);
    try {
      const loggedIn = await login(email.trim(), password);
      const target = from && from !== "/login" ? from : defaultRouteForUser(loggedIn);
      navigate(target, { replace: true });
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message || "No se pudo iniciar sesión.");
      } else {
        setError("No se pudo iniciar sesión. Inténtalo de nuevo.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-6">
          <p className="text-sm font-medium text-slate-500">Licitaciones AI</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">Iniciar sesión</h1>
          <p className="mt-2 text-sm text-slate-600">
            Usa la cuenta de tu empresa para acceder a la plataforma.
          </p>
        </div>

        {authError ? (
          <Alert variant="warning" className="mb-4">
            {authError}
          </Alert>
        ) : null}
        {error ? (
          <Alert variant="error" className="mb-4">
            {error}
          </Alert>
        ) : null}

        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input
            label="Correo electrónico"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            label="Contraseña"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" className="w-full" loading={submitting}>
            Iniciar sesión
          </Button>
        </form>
      </div>
    </main>
  );
}
