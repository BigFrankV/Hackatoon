# Licitaciones AI --- Especificación funcional y técnica integral

**Versión:** 1.0\
**Estado:** Documento base de diseño\
**Alcance:** Definición funcional, arquitectura, módulos, flujos,
seguridad, datos, API, interfaz y plan de implementación.

> **Nota de vigencia:** esta es la especificación objetivo del producto, no un inventario de todo lo implementado. El estado actual y el arranque local se describen en [README.md](./README.md) y [GUIA_PROYECTO.md](./GUIA_PROYECTO.md).

------------------------------------------------------------------------

## 1. Propósito y visión del producto

Licitaciones AI es una plataforma SaaS multiempresa para apoyar a
empresas proveedoras en la evaluación de oportunidades de licitación y
en la preparación de sus ofertas. El sistema centraliza antecedentes
corporativos, permite incorporar documentos de licitaciones, extrae y
estructura requisitos, apoya la decisión Go/No-Go con evidencia trazable
y facilita la preparación de una carpeta de oferta.

La plataforma debe reducir trabajo manual, evitar omisiones, mejorar la
trazabilidad de las decisiones y reutilizar información corporativa sin
mezclar datos entre empresas.

### 1.1 Objetivos

-   Centralizar los antecedentes legales, administrativos, técnicos y
    comerciales de cada empresa.
-   Registrar licitaciones y sus documentos asociados.
-   Extraer requisitos, fechas, montos, garantías, anexos y criterios de
    evaluación.
-   Entregar una evaluación Go/No-Go explicable, sustentada en evidencia
    documental.
-   Permitir consultas mediante chat contextual sobre documentos y
    licitaciones.
-   Reutilizar antecedentes de la bóveda corporativa al preparar
    ofertas.
-   Generar una carpeta de oferta descargable, inicialmente en ZIP, con
    documentos y checklist.
-   Mantener historial, auditoría y separación estricta entre empresas.

### 1.2 Principios de diseño

1.  **Multi-tenancy desde el backend:** toda consulta y modificación de
    datos de empresa se limita al `company_id` obtenido de la identidad
    autenticada.
2.  **La IA no decide reglas determinísticas:** puede extraer, resumir y
    clasificar; fechas, vencimientos, cálculos y reglas duras se validan
    mediante código.
3.  **Resultados explicables:** cada requisito, alerta y conclusión debe
    enlazar al documento, página o fragmento que la sustenta cuando
    exista evidencia.
4.  **Trazabilidad:** registrar quién hizo qué, cuándo y sobre qué
    entidad.
5.  **Seguridad por defecto:** almacenamiento privado, secretos fuera
    del repositorio, autorización en servidor y validación de archivos.
6.  **Arquitectura modular:** separar API, dominio, persistencia,
    procesamiento documental y proveedores de IA.
7.  **Human-in-the-loop:** las recomendaciones de IA son apoyo; el
    usuario revisa y confirma decisiones y documentos finales.

------------------------------------------------------------------------

## 2. Usuarios, empresas y permisos

### 2.1 Roles globales

  -----------------------------------------------------------------------
  Rol                     Ámbito                  Responsabilidad
  ----------------------- ----------------------- -----------------------
  `super_admin`           Plataforma              Administra empresas y
                                                  usuarios de la
                                                  plataforma, soporte y
                                                  configuración global.

  `admin`                 Una empresa             Administra usuarios,
                                                  bóveda, licitaciones y
                                                  configuración de su
                                                  empresa.

  `user`                  Una empresa             Ejecuta tareas
                                                  operativas autorizadas:
                                                  consultar bóveda,
                                                  analizar licitaciones y
                                                  preparar ofertas.
  -----------------------------------------------------------------------

El rol no reemplaza los permisos por recurso. Se recomienda una matriz
centralizada de permisos para que cada endpoint y vista aplique la misma
política.

### 2.2 Reglas de pertenencia

-   `super_admin` tiene `company_id = NULL` y opera en el ámbito global.
-   `admin` y `user` tienen obligatoriamente un `company_id`.
-   El `company_id` de un usuario normal nunca se recibe como autoridad
    desde el frontend.
-   Para usuarios `admin` y `user`, la empresa activa se obtiene del
    usuario autenticado.
-   Las operaciones globales de `super_admin` deben requerir permisos
    específicos y quedar auditadas.
-   El acceso de soporte de un `super_admin` a datos de una empresa debe
    ser explícito, justificado y registrado.

### 2.3 Matriz funcional resumida

  ----------------------------------------------------------------------------------
  Capacidad                        super_admin              admin               user
  ------------------------- ------------------ ------------------ ------------------
  Ver panel global                          Sí                 No                 No

  Crear/editar/desactivar                   Sí                 No                 No
  empresas                                                        

  Crear usuarios en                         Sí                 No                 No
  cualquier empresa                                               

  Administrar usuarios de       Soporte/global                 Sí                 No
  su empresa                                                      

  Editar su perfil y                        Sí                 Sí                 Sí
  contraseña                                                      

  Ver bóveda de su empresa      Solo acceso de                 Sí                 Sí
                              soporte auditado                    

  Administrar categorías y      Global/soporte                 Sí      Según permiso
  documentos de bóveda                auditado                    

  Crear y administrar           Global/soporte                 Sí       Sí, sujeto a
  licitaciones                        auditado                               permiso

  Ejecutar análisis             Global/soporte                 Sí                 Sí
                                      auditado                    

  Aprobar/confirmar             Según política                 Sí      Según permiso
  Go/No-Go                                                        

  Crear carpeta de oferta       Global/soporte                 Sí                 Sí
                                      auditado                    

  Administrar configuración          No aplica                 Sí                 No
  de empresa                       globalmente                    

  Consultar auditoría                   Global      De su empresa     Solo actividad
                                                                       propia, si se
                                                                            habilita
  ----------------------------------------------------------------------------------

La matriz final debe convertirse en permisos concretos, por ejemplo
`users.read`, `users.create`, `tenders.analyze`, `offers.generate`,
`vault.documents.delete`.

------------------------------------------------------------------------

## 3. Alcance funcional por módulos

## 3.1 Autenticación, autorización y cuenta

### Funciones

-   Inicio y cierre de sesión.
-   Renovación de sesión mediante refresh token rotativo.
-   Consulta del usuario autenticado (`/auth/me`).
-   Edición del perfil propio.
-   Cambio de contraseña.
-   Recuperación de contraseña mediante flujo seguro, si se incorpora
    envío de correo.
-   Gestión de sesiones y revocación.
-   Administración de usuarios por parte de administradores autorizados.
-   Control de roles y pertenencia a empresa.
-   Registro de intentos fallidos y eventos de seguridad.

### Reglas

-   Contraseñas con Argon2id.
-   Access token de corta duración, por ejemplo 10--15 minutos.
-   Refresh token aleatorio, almacenado como hash en base de datos y
    enviado en cookie HttpOnly, Secure y SameSite apropiado.
-   Rotación de refresh token en cada renovación y detección de
    reutilización.
-   El frontend no almacena refresh token en `localStorage`.
-   Deshabilitar un usuario o empresa debe impedir nuevas
    autenticaciones y bloquear operaciones protegidas.
-   Un usuario no puede cambiar su propio rol, empresa o estado.
-   Un `admin` no puede crear otro `admin` si la política de negocio no
    se lo permite; la política propuesta permite que admin gestione
    usuarios de su empresa, pero solo `super_admin` asigna `admin`
    inicialmente o eleva privilegios.

## 3.2 Bóveda de Empresa

La bóveda es el repositorio privado de antecedentes reutilizables de una
empresa.

### Tipos de antecedentes sugeridos

-   Identificación y constitución de la empresa.
-   Certificados de vigencia y poderes.
-   Antecedentes tributarios y previsionales.
-   Estados financieros y antecedentes comerciales.
-   Experiencia y contratos anteriores.
-   Certificaciones y acreditaciones.
-   CV y perfiles del equipo.
-   Equipamiento, infraestructura y capacidades técnicas.
-   Declaraciones juradas y formularios frecuentes.
-   Otros documentos definidos por la empresa.

### Funciones

-   Crear categorías y subcategorías.
-   Subir documentos.
-   Ver metadatos y estado de procesamiento.
-   Descargar documentos con autorización.
-   Reemplazar una versión sin borrar el historial.
-   Archivar documentos.
-   Definir vigencia y fecha de vencimiento.
-   Marcar documentos como vigentes, por vencer, vencidos o pendientes
    de revisión.
-   Buscar por nombre, categoría, etiquetas y texto extraído.
-   Consultar historial de versiones.
-   Ver qué licitaciones/ofertas utilizaron un antecedente, cuando se
    implemente la trazabilidad de uso.

### Metadatos mínimos

-   Nombre original y nombre interno.
-   Empresa propietaria (`company_id`).
-   Categoría.
-   Tipo MIME detectado.
-   Tamaño.
-   Hash SHA-256.
-   Ubicación privada del objeto.
-   Usuario que subió el archivo.
-   Fecha de carga.
-   Estado de procesamiento.
-   Fecha de emisión y vencimiento, si corresponde.
-   Número de versión y documento reemplazado.
-   Resultado de validación/antivirus, si está disponible.

### Seguridad documental

-   No almacenar archivos en una carpeta pública del frontend.
-   Validar extensión, MIME real, tamaño y contenido.
-   Usar nombres internos no predecibles.
-   Descargar mediante endpoint autorizado o URL firmada de corta
    duración.
-   Evitar ejecutar o renderizar contenido activo.
-   Registrar cargas, descargas, reemplazos y eliminaciones lógicas.
-   Aplicar límites de tamaño y cuotas por empresa.

## 3.3 Registro y gestión de licitaciones

### Funciones

-   Crear una licitación manualmente.
-   Subir bases administrativas, técnicas, anexos, formularios y
    aclaraciones.
-   Registrar fuente, entidad licitante, identificador, título y URL de
    origen.
-   Registrar fechas clave.
-   Asociar múltiples documentos a una licitación.
-   Consultar estado del procesamiento documental.
-   Editar datos no extraídos o corregir extracción.
-   Archivar licitaciones.
-   Mantener historial de cambios.

### Estados sugeridos

`draft`, `uploaded`, `processing`, `ready_for_review`, `analyzing`,
`analyzed`, `go`, `no_go`, `in_preparation`, `submitted`, `closed`,
`archived`, `failed`.

Los estados deben tener transiciones explícitas. Por ejemplo, una
licitación no debería pasar a `submitted` si no existe una carpeta de
oferta marcada como completa o una confirmación manual.

### Datos relevantes

-   Identificador externo.
-   Nombre/título.
-   Organismo comprador.
-   Descripción.
-   Monto estimado y moneda.
-   Fecha de publicación.
-   Fecha límite de preguntas.
-   Fecha de respuestas.
-   Fecha/hora de cierre.
-   Fecha estimada de adjudicación.
-   Lugar de ejecución.
-   Duración del contrato.
-   Garantías.
-   Requisitos de admisibilidad.
-   Criterios y ponderaciones.
-   Contactos y enlaces.
-   Estado interno.

Las fechas y zonas horarias deben almacenarse de forma consistente,
preferentemente UTC, conservando la zona horaria de origen cuando sea
relevante.

## 3.4 Extracción y procesamiento de documentos

### Flujo

1.  El usuario carga un archivo.
2.  El backend valida extensión, MIME, tamaño y permisos.
3.  Se almacena en repositorio privado.
4.  Se crea un registro de documento y un trabajo de procesamiento.
5.  Un worker extrae texto y metadatos.
6.  Si el PDF es escaneado, se deriva a OCR.
7.  El texto se divide en fragmentos con referencia a página y posición.
8.  Se detectan requisitos, fechas, montos, garantías y criterios.
9.  Se guardan resultados estructurados y evidencias.
10. El usuario revisa y corrige los datos detectados.

### Requisitos de extracción

-   Conservar documento, página y fragmento fuente.
-   No inventar datos ausentes.
-   Diferenciar valor detectado de valor confirmado por usuario.
-   Guardar nivel de confianza como señal orientativa, no como verdad.
-   Mantener versión del extractor/modelo y fecha de procesamiento.
-   Permitir reprocesamiento sin destruir resultados anteriores.

### Formatos iniciales

Priorizar PDF y DOCX. Incorporar XLSX y archivos comprimidos cuando el
alcance y seguridad lo permitan. Los archivos protegidos por contraseña
o corruptos deben quedar en estado de error comprensible.

## 3.5 Análisis de factibilidad Go/No-Go

El análisis debe combinar reglas determinísticas, extracción y
asistencia de IA.

### Dimensiones sugeridas

-   Admisibilidad legal y administrativa.
-   Cumplimiento técnico.
-   Experiencia requerida.
-   Certificaciones y acreditaciones.
-   Capacidad operativa.
-   Capacidad financiera.
-   Garantías exigidas.
-   Plazos y disponibilidad.
-   Riesgos contractuales.
-   Competitividad económica, si existen antecedentes suficientes.

### Resultado

-   Recomendación: `GO`, `NO_GO` o `REVIEW_REQUIRED`.
-   Resumen ejecutivo.
-   Puntaje por dimensión, con explicación.
-   Requisitos obligatorios identificados.
-   Requisitos cumplidos, incumplidos y no verificables.
-   Riesgos críticos.
-   Fechas límite.
-   Antecedentes faltantes en la bóveda.
-   Acciones sugeridas.
-   Evidencias con documento, página y fragmento.
-   Fecha de análisis y versión del motor.

### Reglas de negocio

-   Un requisito obligatorio no acreditado debe elevar una alerta
    crítica.
-   La ausencia de evidencia no equivale automáticamente a
    incumplimiento; se clasifica como "no verificado".
-   La recomendación de IA nunca debe ocultar una causal determinística
    de inadmisibilidad.
-   Los puntajes deben ser configurables y versionados.
-   Un usuario autorizado debe poder confirmar o descartar la
    recomendación, indicando motivo.
-   Registrar quién confirmó el resultado y cuándo.

## 3.6 Chat contextual

### Objetivo

Permitir preguntas sobre una licitación, sus documentos y los
antecedentes de la empresa a los que el usuario tiene acceso.

### Ejemplos

-   "¿Cuál es la fecha de cierre?"
-   "¿Qué garantías exige esta licitación?"
-   "¿Tenemos experiencia que cumpla este requisito?"
-   "¿Qué documentos de la bóveda están vencidos?"
-   "Resume las obligaciones técnicas del proveedor."

### Reglas

-   El contexto se limita a la empresa y a la licitación autorizada.
-   Recuperar fragmentos con búsqueda híbrida: texto/SQL + similitud
    vectorial.
-   Cada respuesta debe mostrar citas y referencias a documento/página
    cuando corresponda.
-   Si no hay evidencia suficiente, responder que no se encontró
    información suficiente.
-   No permitir que instrucciones contenidas en documentos alteren las
    políticas del sistema (defensa frente a prompt injection).
-   No revelar documentos de otras empresas ni información no
    autorizada.
-   Registrar conversaciones y referencias de forma proporcional, con
    políticas de retención.

## 3.7 Generador de carpeta de oferta

### Objetivo

Preparar una estructura de entrega reutilizando documentos de la bóveda
y generando un checklist de faltantes.

### Funciones

-   Crear una carpeta de oferta asociada a una licitación.
-   Identificar documentos requeridos.
-   Sugerir antecedentes de la bóveda que podrían cumplir cada
    requisito.
-   Permitir seleccionar versión de cada antecedente.
-   Generar documentos o plantillas cuando se habilite esa capacidad.
-   Completar formularios solo con datos respaldados.
-   Marcar elementos como pendiente, listo, revisado o no aplica.
-   Validar vigencia y coherencia de antecedentes.
-   Generar ZIP con estructura ordenada.
-   Registrar versión, autor, fecha y archivos incluidos.
-   Permitir regenerar una versión sin sobrescribir la anterior.

### Estructura de ZIP sugerida

``` text
oferta_<identificador>/
  00_indice/
    indice_oferta.pdf
    checklist.xlsx
  01_administrativo/
  02_tecnico/
  03_economico/
  04_declaraciones/
  05_anexos/
```

La estructura real debe ser configurable según las bases de cada
licitación. El sistema no debe afirmar que una oferta está lista para
enviar si quedan requisitos obligatorios sin revisar.

## 3.8 Paneles y reportes

### Panel de empresa

-   Licitaciones activas.
-   Próximos cierres.
-   Análisis pendientes de revisión.
-   Oportunidades Go/No-Go.
-   Documentos vencidos o próximos a vencer.
-   Ofertas en preparación.
-   Actividad reciente.

### Panel de plataforma

Solo para `super_admin`: - Empresas activas/inactivas. - Usuarios por
empresa. - Uso de almacenamiento. - Trabajos de procesamiento
fallidos. - Estado general de servicios. - Eventos de seguridad
relevantes.

No exponer contenido documental de empresas en el panel global salvo
flujo de soporte autorizado y auditado.

------------------------------------------------------------------------

## 4. Arquitectura técnica

## 4.1 Stack base

  Capa            Tecnología
  --------------- --------------------------------------------------------
  Frontend        React, Vite, TypeScript, Tailwind CSS
  Backend         Python 3.12+, FastAPI
  Validación      Pydantic v2
  ORM             SQLAlchemy 2 async
  Migraciones     Alembic
  Base de datos   PostgreSQL 16
  Vector search   pgvector
  Contraseñas     Argon2id
  Tokens          JWT access + refresh aleatorio opaco
  Procesamiento   Worker asíncrono y cola de trabajos
  Archivos        Almacenamiento privado compatible con S3 o equivalente
  Contenedores    Docker y Docker Compose
  Pruebas         Pytest, HTTPX; Vitest/Testing Library en frontend

Las versiones deben fijarse y actualizarse mediante pruebas; evitar
depender indefinidamente de rangos abiertos en producción.

## 4.2 Organización backend

``` text
backend/
  app/
    main.py
    api/
      dependencies/
      v1/
        auth.py
        users.py
        companies.py
        vault.py
        tenders.py
        analysis.py
        chat.py
        offers.py
    core/
      config.py
      security.py
      permissions.py
      logging.py
      exceptions.py
    db/
      base.py
      session.py
    models/
      user.py
      company.py
      refresh_token.py
      audit_log.py
      document.py
      tender.py
      requirement.py
      analysis.py
      conversation.py
      offer.py
    schemas/
    repositories/
    services/
    workers/
    integrations/
      storage/
      ai/
      extraction/
    tests/
  alembic/
  alembic.ini
  requirements.txt
  Dockerfile
```

Responsabilidades: - `api`: HTTP, validación de entrada y respuesta. -
`dependencies`: sesión DB, usuario autenticado y permisos. - `core`:
configuración, seguridad, excepciones y logging. - `models`: entidades
SQLAlchemy. - `schemas`: contratos Pydantic. - `repositories`: consultas
y persistencia. - `services`: reglas de negocio y coordinación. -
`workers`: procesamiento fuera del ciclo HTTP. - `integrations`:
proveedores externos intercambiables.

## 4.3 Organización frontend

``` text
frontend/src/
  app/
    router/
    providers/
  components/
    ui/
    layout/
    feedback/
  features/
    auth/
    dashboard/
    companies/
    users/
    vault/
    tenders/
    analysis/
    chat/
    offers/
    settings/
  hooks/
  lib/
    api/
    auth/
    permissions/
    validation/
  types/
```

Cada feature debe separar páginas, componentes, hooks, servicios API,
esquemas y tipos. Las rutas protegidas mejoran la experiencia, pero no
sustituyen la autorización del backend.

## 4.4 Infraestructura Docker

Servicios previstos: - `frontend` - `backend` - `db` (PostgreSQL +
pgvector) - `worker` - opcionalmente `redis` como broker/cache si la
cola seleccionada lo requiere.

En desarrollo se pueden montar volúmenes para hot reload. En
producción: - no ejecutar `--reload`; - no exponer PostgreSQL
públicamente; - usar secretos gestionados; - configurar backups y
restauración; - healthchecks; - logs centralizados; - TLS en el proxy; -
límites de CPU/memoria; - separar red interna de base de datos.

------------------------------------------------------------------------

## 5. Modelo de datos propuesto

Este es un modelo lógico inicial; debe evolucionar con migraciones
revisadas.

### 5.1 Núcleo de identidad

-   `companies`: empresa, identificador tributario, nombre legal,
    estado, configuración y fechas.
-   `users`: email normalizado, nombre, apellido, hash de contraseña,
    rol, `company_id`, estado, último acceso.
-   `refresh_tokens`: hash del token, usuario, familia, expiración,
    revocación, reemplazo y metadatos mínimos.
-   `audit_logs`: actor, empresa, acción, entidad, identificador, fecha,
    IP y metadatos filtrados.

### 5.2 Documentos y bóveda

-   `document_categories`
-   `documents`
-   `document_versions`
-   `document_extractions`
-   `document_chunks`
-   `document_access_events` (si se requiere analítica separada de
    auditoría)

### 5.3 Licitaciones y análisis

-   `tenders`
-   `tender_documents`
-   `tender_requirements`
-   `tender_milestones`
-   `tender_analyses`
-   `analysis_findings`
-   `analysis_evidence`
-   `analysis_decisions`

### 5.4 Chat y ofertas

-   `conversations`
-   `messages`
-   `message_citations`
-   `offers`
-   `offer_items`
-   `offer_versions`
-   `offer_files`
-   `offer_checklist_items`

### 5.5 Reglas de integridad

-   Las tablas pertenecientes a una empresa deben incluir `company_id`,
    salvo catálogos verdaderamente globales.
-   Índices compuestos por `company_id` y campos de búsqueda frecuentes.
-   Foreign keys y constraints para impedir relaciones cruzadas entre
    empresas.
-   Soft delete donde se necesite historial, con reglas claras de
    retención.
-   Guardar fechas en UTC.
-   Evitar almacenar secretos o tokens en texto plano.
-   No guardar el contenido completo de archivos en tablas relacionales
    si se utiliza object storage.

------------------------------------------------------------------------

## 6. Diseño de API REST

Prefijo sugerido: `/api/v1`.

### 6.1 Convenciones

-   JSON para operaciones normales.
-   `multipart/form-data` para cargas.
-   Paginación consistente (`page`, `page_size` o cursor).
-   Filtros explícitos y ordenamiento permitido por lista blanca.
-   Códigos HTTP coherentes: 200, 201, 204, 400, 401, 403, 404, 409,
    422, 429, 500.
-   Respuestas de error con código estable y mensaje seguro.
-   Nunca confiar en `company_id` enviado por un usuario normal.
-   No devolver trazas internas ni detalles sensibles.

### 6.2 Endpoints funcionales iniciales

  ----------------------------------------------------------------------------
  Recurso                             Endpoints principales
  ----------------------------------- ----------------------------------------
  Auth                                `POST /auth/login`,
                                      `POST /auth/refresh`,
                                      `POST /auth/logout`, `GET /auth/me`,
                                      `PATCH /auth/me`,
                                      `POST /auth/change-password`

  Empresas                            `GET /companies`, `POST /companies`,
                                      `GET /companies/{id}`,
                                      `PATCH /companies/{id}`,
                                      `POST /companies/{id}/deactivate`

  Usuarios                            `GET /users`, `POST /users`,
                                      `GET /users/{id}`, `PATCH /users/{id}`,
                                      `POST /users/{id}/deactivate`,
                                      `POST /users/{id}/reset-password`

  Bóveda                              `GET/POST /vault/categories`,
                                      `GET/POST /vault/documents`,
                                      `GET /vault/documents/{id}`,
                                      `POST /vault/documents/{id}/versions`,
                                      `GET /vault/documents/{id}/download`

  Licitaciones                        `GET/POST /tenders`,
                                      `GET/PATCH /tenders/{id}`,
                                      `POST /tenders/{id}/documents`,
                                      `POST /tenders/{id}/archive`

  Análisis                            `POST /tenders/{id}/analyses`,
                                      `GET /tenders/{id}/analyses`,
                                      `GET /analyses/{id}`,
                                      `POST /analyses/{id}/decision`

  Chat                                `POST /tenders/{id}/conversations`,
                                      `GET /conversations/{id}`,
                                      `POST /conversations/{id}/messages`

  Ofertas                             `GET/POST /tenders/{id}/offers`,
                                      `GET/PATCH /offers/{id}`,
                                      `POST /offers/{id}/generate`,
                                      `GET /offers/{id}/download`

  Auditoría                           `GET /audit-logs` según rol y alcance
  ----------------------------------------------------------------------------

La lista es un contrato inicial, no implica que todos los endpoints
deban implementarse en el MVP.

------------------------------------------------------------------------

## 7. Requisitos no funcionales

### Seguridad

-   Autenticación robusta y autorización en backend.
-   Aislamiento multiempresa en todas las consultas.
-   Protección contra IDOR, SQL injection, XSS, CSRF y abuso de API.
-   Rate limiting y límites de carga.
-   Gestión segura de secretos.
-   Registro de eventos relevantes.
-   Dependencias actualizadas y escaneo de vulnerabilidades.

### Rendimiento

-   Paginación en listados.
-   Procesamiento pesado fuera del request HTTP.
-   Índices y consultas medidas.
-   Límites de concurrencia para extracción e IA.
-   Cache solo para datos no sensibles o con aislamiento correcto.

### Disponibilidad y recuperación

-   Backups automáticos de PostgreSQL.
-   Pruebas periódicas de restauración.
-   Reintentos idempotentes en workers.
-   Cola de fallos o dead-letter para trabajos que agoten reintentos.
-   Monitoreo de latencia, errores y trabajos pendientes.

### Accesibilidad y UX

-   Formularios con validación clara.
-   Estados de carga, vacío, error y éxito.
-   Confirmación para acciones destructivas.
-   Tablas con filtros y paginación.
-   Diseño adaptable.
-   Navegación por teclado y etiquetas accesibles.

------------------------------------------------------------------------

## 8. Estrategia de pruebas

### Backend

-   Unitarias de servicios y reglas de negocio.
-   Integración con PostgreSQL real de pruebas.
-   Pruebas de autorización por rol.
-   Pruebas de aislamiento entre dos empresas.
-   Pruebas de refresh token y reutilización.
-   Pruebas de cargas inválidas y límites.
-   Pruebas de endpoints y códigos de error.

### Frontend

-   Componentes y formularios.
-   Flujos de login/logout/refresh.
-   Renderizado según permisos.
-   Manejo de sesión expirada.
-   Estados de error y carga.
-   Pruebas E2E de flujos críticos.

### Casos críticos multi-tenant

1.  Usuario de empresa A no puede leer un recurso de empresa B aunque
    conozca su UUID.
2.  Usuario de empresa A no puede modificar ni eliminar recursos de B.
3.  Cambiar `company_id` en el body o query no cambia el ámbito
    autorizado.
4.  Un admin no puede asignarse `super_admin`.
5.  Un usuario desactivado no puede seguir utilizando refresh tokens.
6.  Un documento descargable requiere autorización sobre el recurso y
    empresa.
7.  Un chat no recupera fragmentos de otra empresa.
8.  Un trabajo asíncrono conserva y valida el contexto de empresa.

------------------------------------------------------------------------

## 9. MVP recomendado y etapas

### Etapa 0 --- Base técnica

-   Repositorio, Docker Compose y variables de entorno.
-   Frontend y backend levantan.
-   PostgreSQL con pgvector.
-   Healthchecks y documentación API.

### Etapa 1 --- Identidad y multi-tenancy

-   Modelos Company y User.
-   Migraciones Alembic.
-   Login, refresh rotativo, logout y `/me`.
-   CRUD de empresas y usuarios según rol.
-   Perfil propio y cambio de contraseña.
-   Auditoría.
-   Pruebas de aislamiento entre empresas.

### Etapa 2 --- Bóveda

-   Categorías.
-   Carga y descarga privada.
-   Metadatos, vigencia y versiones.
-   Extracción de texto inicial.

### Etapa 3 --- Licitaciones

-   CRUD de licitaciones.
-   Carga de bases y anexos.
-   Fechas y estados.
-   Extracción estructurada revisable.

### Etapa 4 --- Go/No-Go

-   Catálogo de requisitos.
-   Reglas determinísticas.
-   Hallazgos y evidencias.
-   Recomendación y decisión humana.

### Etapa 5 --- Chat contextual

-   Fragmentación e indexación.
-   Recuperación híbrida.
-   Respuestas con citas.
-   Pruebas contra filtración entre empresas.

### Etapa 6 --- Carpeta de oferta

-   Checklist.
-   Vinculación de documentos de bóveda.
-   Versionado de oferta.
-   Generación ZIP.

### Etapa 7 --- Endurecimiento

-   Backups y restauración.
-   Monitoreo.
-   Rate limits.
-   Seguridad de archivos.
-   Pruebas E2E y revisión de permisos.

------------------------------------------------------------------------

## 10. Criterios de aceptación globales

El MVP se considera funcional cuando:

-   Los tres roles pueden autenticarse y reciben permisos acordes.
-   Un `super_admin` puede crear empresas y administrar sus
    administradores.
-   Un `admin` administra usuarios de su empresa sin acceder a otra.
-   Un `user` puede realizar las tareas operativas habilitadas y no
    puede administrar la empresa.
-   El perfil propio puede consultarse y editarse sin permitir elevar
    privilegios.
-   Los documentos y licitaciones quedan aislados por empresa.
-   El análisis identifica evidencia y distingue incumplido de no
    verificado.
-   La carpeta de oferta puede generarse con checklist y archivos
    seleccionados.
-   Las acciones relevantes quedan auditadas.
-   Existen pruebas automatizadas que demuestran que no hay acceso
    cruzado entre empresas.

------------------------------------------------------------------------

## 11. Decisiones pendientes que deben cerrarse antes de producción

1.  Proveedor de correo para invitaciones y recuperación de contraseña.
2.  Proveedor de almacenamiento privado.
3.  Motor OCR y formatos soportados.
4.  Cola de trabajos y política de reintentos.
5.  Proveedor/modelo de IA y estrategia de costos.
6.  Política exacta de permisos para `user`.
7.  Si se permite más de un `admin` por empresa.
8.  Retención y eliminación de documentos y conversaciones.
9.  Política de acceso de soporte de `super_admin`.
10. Requisitos legales y de privacidad aplicables al tipo de
    antecedentes almacenados.

**Nota:** este documento es una especificación de diseño. Antes de
producción deben completarse revisión de seguridad, pruebas, políticas
de privacidad, backups y validación con usuarios del negocio.
