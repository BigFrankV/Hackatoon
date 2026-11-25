import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiRequestError } from "@/lib/api/client";
import { createCompany } from "@/lib/api/companies";
import type { CompanyCreateResponse } from "@/types";

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

export function CompanyCreatePage() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompanyCreateResponse | null>(null);

  const [form, setForm] = useState({
    legal_name: "",
    display_name: "",
    tax_id: "",
    email: "",
    phone: "",
    address: "",
    admin_first_name: "",
    admin_last_name: "",
    admin_email: "",
  });

  const update = (key: keyof typeof form, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);

    if (!form.legal_name.trim()) return setError("La razón social es obligatoria.");
    if (!form.admin_first_name.trim() || !form.admin_last_name.trim() || !form.admin_email.trim()) {
      return setError("El nombre, el apellido y el correo electrónico del administrador inicial son obligatorios.");
    }

    setSaving(true);
    try {
      const response = await createCompany({
        legal_name: form.legal_name.trim(),
        display_name: emptyToNull(form.display_name),
        tax_id: emptyToNull(form.tax_id),
        email: emptyToNull(form.email),
        phone: emptyToNull(form.phone),
        address: emptyToNull(form.address),
        initial_admin: {
          first_name: form.admin_first_name.trim(),
          last_name: form.admin_last_name.trim(),
          email: form.admin_email.trim(),
        },
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "No se pudo crear la empresa.");
    } finally {
      setSaving(false);
    }
  };

  if (result) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Empresa creada</h1>
          <p className="mt-1 text-sm text-slate-600">
            La empresa y su administrador inicial se crearon correctamente.
          </p>
        </div>

        <Alert variant="success">La empresa "{result.company.legal_name}" se creó correctamente.</Alert>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Administrador inicial</h2>
            <p className="text-sm text-slate-600">
              {result.initial_admin.first_name} {result.initial_admin.last_name} ({result.initial_admin.email})
            </p>
          </div>
          {result.initial_admin.temporary_password ? (
            <Alert variant="warning">
              <p className="font-medium">Contraseña temporal (compartir de forma segura)</p>
              <p className="mt-1 font-mono text-sm">{result.initial_admin.temporary_password}</p>
            </Alert>
          ) : null}
          <Alert variant="info">
            <p className="font-medium">Entrega</p>
            <p className="mt-1">{result.delivery.note}</p>
          </Alert>
          <div className="flex gap-3">
            <Link to={`/platform/companies/${result.company.id}`}>
              <Button>Ver empresa</Button>
            </Link>
            <Button variant="secondary" onClick={() => navigate("/platform/companies")}>
              Volver a empresas
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Crear empresa</h1>
        <p className="mt-1 text-sm text-slate-600">
          Crea una empresa nueva y su administrador inicial.
        </p>
      </div>

      <form className="space-y-6" onSubmit={handleSubmit}>
        {error ? <Alert variant="error">{error}</Alert> : null}

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Datos de la empresa</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input label="Razón social" name="legal_name" value={form.legal_name} onChange={(e) => update("legal_name", e.target.value)} required />
            <Input label="Nombre visible" name="display_name" value={form.display_name} onChange={(e) => update("display_name", e.target.value)} />
            <Input label="ID fiscal" name="tax_id" value={form.tax_id} onChange={(e) => update("tax_id", e.target.value)} />
            <Input label="Correo electrónico" name="email" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
            <Input label="Teléfono" name="phone" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
            <Input label="Dirección" name="address" value={form.address} onChange={(e) => update("address", e.target.value)} />
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Administrador inicial</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input label="Nombre" name="admin_first_name" value={form.admin_first_name} onChange={(e) => update("admin_first_name", e.target.value)} required />
            <Input label="Apellido" name="admin_last_name" value={form.admin_last_name} onChange={(e) => update("admin_last_name", e.target.value)} required />
            <Input label="Correo electrónico" name="admin_email" type="email" value={form.admin_email} onChange={(e) => update("admin_email", e.target.value)} required />
          </div>
        </section>

        <div className="flex gap-3">
          <Button type="submit" loading={saving}>Crear empresa</Button>
          <Button type="button" variant="secondary" onClick={() => navigate("/platform/companies")}>
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  );
}
