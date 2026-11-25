import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ApiRequestError } from "@/lib/api/client";
import { listCompanies } from "@/lib/api/companies";
import { createGlobalUser } from "@/lib/api/users";
import type { CompanyResponse, UserCreatedResponse, UserRole, UserStatus } from "@/types";

export function PlatformUserCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [companies, setCompanies] = useState<CompanyResponse[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UserCreatedResponse | null>(null);

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    role: "user" as UserRole,
    company_id: searchParams.get("company_id") || "",
    status: "invited" as UserStatus,
  });

  useEffect(() => {
    listCompanies({ page: 1, page_size: 100 })
      .then((res) => setCompanies(res.items))
      .catch(() => undefined);
  }, []);

  const update = (key: keyof typeof form, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!form.first_name.trim() || !form.last_name.trim() || !form.email.trim()) {
      return setError("El nombre, el apellido y el correo electrónico son obligatorios.");
    }
    if (form.role !== "super_admin" && !form.company_id) {
      return setError("La empresa es obligatoria para los roles de administrador y usuario.");
    }

    setSaving(true);
    try {
      const response = await createGlobalUser({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        role: form.role,
        company_id: form.role === "super_admin" ? null : form.company_id,
        status: form.status,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo crear el usuario.");
    } finally {
      setSaving(false);
    }
  };

  if (result) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Usuario creado</h1>
          <p className="mt-1 text-sm text-slate-600">El usuario se creó correctamente.</p>
        </div>
        <Alert variant="success">
          {result.user.first_name} {result.user.last_name} ({result.user.email}) se creó correctamente.
        </Alert>
        {result.temporary_password ? (
          <Alert variant="warning">
            <p className="font-medium">Contraseña temporal (compartir de forma segura)</p>
            <p className="mt-1 font-mono text-sm">{result.temporary_password}</p>
          </Alert>
        ) : null}
        <Alert variant="info">{result.delivery.note}</Alert>
        <div className="flex gap-3">
          <Link to={`/platform/users/${result.user.id}`}><Button>Ver usuario</Button></Link>
          <Button variant="secondary" onClick={() => navigate("/platform/users")}>Volver a usuarios</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Crear usuario</h1>
        <p className="mt-1 text-sm text-slate-600">Crea un usuario en cualquier empresa o un superadministrador de la plataforma.</p>
      </div>

      <form className="space-y-6" onSubmit={handleSubmit}>
        {error ? <Alert variant="error">{error}</Alert> : null}
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="grid gap-4 md:grid-cols-2">
            <Input label="Nombre" name="first_name" value={form.first_name} onChange={(e) => update("first_name", e.target.value)} required />
            <Input label="Apellido" name="last_name" value={form.last_name} onChange={(e) => update("last_name", e.target.value)} required />
            <Input label="Correo electrónico" name="email" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} required />
            <Select
              label="Rol"
              name="role"
              value={form.role}
              onChange={(e) => update("role", e.target.value)}
              options={[
                { value: "user", label: "Usuario" },
                { value: "admin", label: "Administrador" },
                { value: "super_admin", label: "Superadministrador" },
              ]}
            />
            <Select
              label="Empresa"
              name="company_id"
              value={form.company_id}
              onChange={(e) => update("company_id", e.target.value)}
              disabled={form.role === "super_admin"}
              placeholder={form.role === "super_admin" ? "Sin empresa (plataforma)" : "Seleccionar empresa"}
              options={companies.map((c) => ({ value: c.id, label: c.display_name || c.legal_name }))}
            />
            <Select
              label="Estado"
              name="status"
              value={form.status}
              onChange={(e) => update("status", e.target.value)}
              options={[
                { value: "invited", label: "Invitado" },
                { value: "active", label: "Activo" },
                { value: "inactive", label: "Inactivo" },
              ]}
            />
          </div>
        </section>
        <div className="flex gap-3">
          <Button type="submit" loading={saving}>Crear usuario</Button>
          <Button type="button" variant="secondary" onClick={() => navigate("/platform/users")}>Cancelar</Button>
        </div>
      </form>
    </div>
  );
}
