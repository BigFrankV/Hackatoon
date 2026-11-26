# Mercado Público API Research

**Checked**: 2026-11-26
**Source**: [Official ChileCompra API information](https://www.chilecompra.cl/api/)

## Verified from the Official Information Page

- The official page describes public API access to procurement information,
  including tenders, purchase orders, buyers, and suppliers.
- API access requires requesting a ticket through the official form with Clave
  Única; the ticket is sent to the registered email.
- The published tender service is
  `https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json`.
  The page also lists XML and JSONP representations.
- Documented query forms include tender code, date, state, supplier code, and
  public-organization code. Date examples use `ddmmaaaa`.
- The page says date/state listings return basic information; looking up by
  tender code returns detailed information.
- The page lists tender status codes: published `5`, closed `6`, deserted `7`,
  awarded `8`, revoked `18`, and suspended `19`.
- The official page displayed a banner image named
  `banner-indisponibilidad-api` when checked. Its explanatory text was not
  available in the page text, so current service availability and the duration
  of any interruption must be confirmed before relying on the API.

## Not Verified Yet

- Whether the service and ticket issuance are currently available to this
  project.
- Exact documented response schemas, pagination/volume behavior, rate limits,
  timeout expectations, and terms for caching/retaining source data.
- Whether tender attachments can be discovered and downloaded through the API,
  through the tender website, or only by user-provided files.
- The current validity/rotation rules for tickets.
- Required handling of archived tender types and status transitions.

The official page links a tender API guide and a tender-documentation page, but
the guide's PDF content and attachment availability were not machine-verified
in this review. Do not assume that source document URLs are returned or
downloadable.

## Planning Implications

- Treat the API as an external source adapter and persist provenance/freshness
  separately from company tracking state.
- Keep any ticket in server-side configuration; the published examples place it
  in the query string, so application/proxy logs must not record the full
  upstream URL.
- Keep manual document upload as an independent fallback, as already confirmed
  in the feature specification.
- Before implementation, obtain a valid project ticket and test representative
  list-by-date/state and detail-by-code responses, errors, availability, and
  attachment behavior.

## Sources

- [ChileCompra API page](https://www.chilecompra.cl/api/) (official; updated
  2026-11-19 on the page).
- [Official tender API guide PDF](https://www.chilecompra.cl/wp-content/uploads/2026/03/Documentacion-API-Mercado-Publico-Licitaciones.pdf)
  (linked by the official page; not text-verified in this review).
- [Official API tender documentation endpoint](https://api.mercadopublico.cl/modules/Licitacion.aspx)
  (redirected to the same API overview during this check).
