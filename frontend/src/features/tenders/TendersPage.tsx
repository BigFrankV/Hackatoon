import { FormEvent, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { ApiRequestError } from "@/lib/api/client";
import { getTenderById, type TenderDetail } from "@/lib/api/tenders";

const tenderCodePattern = /^\d+-\d+-[A-Za-z0-9]+$/;

function lookupErrorMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.code === "tender_not_found") return "No se encontró una licitación con ese código.";
    if (error.code === "procurement_ticket_missing" || error.code === "source_ticket_invalid") {
      return "La conexión con Mercado Público no está configurada. Contacta al administrador.";
    }
    if (error.code === "source_timeout") {
      return "Mercado Público no respondió a tiempo. Intenta nuevamente.";
    }
    return error.message;
  }
  return "No se pudo consultar la licitación. Intenta nuevamente.";
}

export function TendersPage() {
  const [code, setCode] = useState("");
  const [tender, setTender] = useState<TenderDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const externalId = code.trim();
    if (!tenderCodePattern.test(externalId) || busy) {
      setError("Ingresa un código válido, por ejemplo 2415-30-LP26.");
      return;
    }
    setBusy(true);
    setError(null);
    setTender(null);
    try {
      setTender(await getTenderById(externalId));
    } catch (requestError) {
      setError(lookupErrorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Licitaciones</h1>
        <p className="mt-1 text-sm text-slate-600">
          Consulta la ficha pública de Mercado Público usando el código de la licitación.
        </p>
      </div>

      <Alert variant="info">
        Esta primera versión consulta y muestra información pública. Todavía no guarda licitaciones
        en seguimiento ni descarga sus documentos.
      </Alert>
      {error ? <Alert variant="error">{error}</Alert> : null}

      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row"
      >
        <label htmlFor="tender-code" className="sr-only">
          Código de licitación
        </label>
        <input
          id="tender-code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          maxLength={40}
          placeholder="Ejemplo: 2415-30-LP26"
          className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
        />
        <button
          type="submit"
          disabled={!code.trim() || busy}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Buscando..." : "Buscar por código"}
        </button>
      </form>

      {tender ? (
        <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col justify-between gap-3 sm:flex-row">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {tender.external_id}
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">{tender.title}</h2>
            </div>
            {tender.status ? (
              <span className="h-fit rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
                {tender.status}
                {tender.status_code ? ` · ${tender.status_code}` : ""}
              </span>
            ) : null}
          </div>

          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            {tender.buyer_name ? (
              <div>
                <dt className="font-medium text-slate-500">Organismo comprador</dt>
                <dd className="mt-1 text-slate-900">{tender.buyer_name}</dd>
              </div>
            ) : null}
            {tender.buyer_code ? (
              <div>
                <dt className="font-medium text-slate-500">Código del organismo</dt>
                <dd className="mt-1 text-slate-900">{tender.buyer_code}</dd>
              </div>
            ) : null}
            {tender.published_at ? (
              <div>
                <dt className="font-medium text-slate-500">Publicación</dt>
                <dd className="mt-1 text-slate-900">{tender.published_at}</dd>
              </div>
            ) : null}
            {tender.closing_at ? (
              <div>
                <dt className="font-medium text-slate-500">Cierre</dt>
                <dd className="mt-1 text-slate-900">{tender.closing_at}</dd>
              </div>
            ) : null}
            {tender.estimated_amount ? (
              <div>
                <dt className="font-medium text-slate-500">Monto estimado</dt>
                <dd className="mt-1 text-slate-900">
                  {tender.estimated_amount} {tender.currency ?? ""}
                </dd>
              </div>
            ) : null}
          </dl>

          {tender.description ? (
            <div>
              <h3 className="font-medium text-slate-700">Descripción</h3>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                {tender.description}
              </p>
            </div>
          ) : null}

          {tender.items.length > 0 ? (
            <div>
              <h3 className="font-medium text-slate-700">Productos o servicios</h3>
              <ul className="mt-2 divide-y divide-slate-100 rounded-md border border-slate-200">
                {tender.items.map((item, index) => (
                  <li key={`${item.name ?? "item"}-${index}`} className="p-3 text-sm">
                    <p className="font-medium text-slate-900">{item.name ?? "Ítem"}</p>
                    {item.description ? (
                      <p className="mt-1 text-slate-600">{item.description}</p>
                    ) : null}
                    {item.quantity || item.unit ? (
                      <p className="mt-1 text-xs text-slate-500">
                        {[item.quantity, item.unit].filter(Boolean).join(" ")}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <a
            href={tender.official_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex text-sm font-medium text-slate-800 underline"
          >
            Abrir ficha oficial en Mercado Público
          </a>
        </section>
      ) : null}
    </div>
  );
}
