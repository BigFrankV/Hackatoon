# Licitaciones AI --- Especificación de autenticación, RBAC, multi-tenancy y administración

**Versión:** 1.0\
**Estado:** Diseño detallado para implementación\
**Prioridad:** Primera fase funcional del producto

------------------------------------------------------------------------

## 1. Objetivo y alcance

Definir el módulo completo de identidad y administración de
usuarios/empresas para Licitaciones AI. Incluye autenticación, sesiones,
perfil personal, autorización por roles, aislamiento multiempresa, CRUD
de empresas, CRUD de usuarios, vistas frontend, endpoints, auditoría,
validaciones y criterios de aceptación.

El diseño contempla tres roles:

-   `super_admin`: administra la plataforma y las empresas.
-   `admin`: administra usuarios y configuración de su empresa.
-   `user`: usuario operativo de una empresa; consulta y trabaja con los
    módulos habilitados, pero no administra la estructura de la empresa.

**Principio central:** la autorización se aplica en backend. Ocultar
botones o rutas en React no constituye seguridad.

------------------------------------------------------------------------

## 2. Modelo de roles y alcance

### 2.1 `super_admin`

Usuario global de plataforma. No pertenece a una empresa.

-   `company_id` debe ser `NULL`.
-   Puede crear, consultar, editar, activar y desactivar empresas.
-   Puede crear administradores y usuarios asociados a una empresa.
-   Puede consultar y administrar usuarios globalmente.
-   Puede suspender cuentas por motivos operativos o de seguridad.
-   Puede consultar métricas globales y auditoría global.
-   No debe tener acceso silencioso e ilimitado al contenido privado de
    todas las empresas.
-   Si necesita soporte sobre una empresa, debe ejecutar un flujo
    explícito de acceso de soporte con motivo, alcance y auditoría.

### 2.2 `admin`

Administrador de una empresa.

-   `company_id` obligatorio.
-   Puede consultar y editar los datos permitidos de su empresa.
-   Puede listar, crear, consultar, editar, activar y desactivar
    usuarios de su empresa.
-   Puede asignar el rol `user`.
-   La asignación o promoción a `admin` queda reservada a `super_admin`
    en la política inicial.
-   No puede cambiar su propio rol ni trasladarse a otra empresa.
-   Puede editar su perfil y cambiar su contraseña.
-   Puede administrar la configuración funcional de su empresa.
-   No puede consultar ni modificar empresas o usuarios de otras
    empresas.

### 2.3 `user`

Usuario operativo de empresa.

-   `company_id` obligatorio.
-   Puede consultar y editar su propio perfil, con campos limitados.
-   Puede cambiar su contraseña.
-   Puede consultar los módulos de operación autorizados.
-   Puede crear y trabajar licitaciones, análisis y ofertas si la
    política de permisos de negocio lo habilita.
-   No puede crear usuarios.
-   No puede modificar roles, estado de usuarios ni datos de la empresa.
-   No puede consultar auditoría administrativa.
-   No puede modificar su `company_id`, rol, estado o permisos.

El rol `user` no debe quedar como una cuenta sin utilidad: es el usuario
que ejecuta el trabajo diario. La administración de usuarios y empresa
se reserva a `admin`, mientras que `user` opera los procesos.

------------------------------------------------------------------------

## 3. Matriz de permisos

La matriz siguiente define la política inicial. Los permisos deben
centralizarse en backend y reutilizarse en la interfaz.

  -----------------------------------------------------------------------------
  Funcionalidad               super_admin              admin               user
  -------------------- ------------------ ------------------ ------------------
  Ver dashboard global                 Sí                 No                 No

  Ver dashboard de      Acceso de soporte                 Sí          Sí, vista
  empresa                        auditado                             operativa

  Ver perfil propio                    Sí                 Sí                 Sí

  Editar perfil propio                 Sí                 Sí                 Sí

  Cambiar contraseña                   Sí                 Sí                 Sí
  propia                                                     

  Ver lista global de                  Sí                 No                 No
  empresas                                                   

  Crear empresa                        Sí                 No                 No

  Ver detalle de                       Sí                 No                 No
  cualquier empresa                                          

  Editar empresa                       Sí                 No                 No

  Activar/desactivar                   Sí                 No                 No
  empresa                                                    

  Crear usuario en                     Sí                 No                 No
  cualquier empresa                                          

  Ver usuarios de                      Sí                 No                 No
  cualquier empresa                                          

  Crear usuario `user`                 No                 Sí                 No
  en su empresa                                              

  Editar usuario                       No                 Sí                 No
  `user` de su empresa                                       

  Desactivar usuario                   No                 Sí                 No
  de su empresa                                              

  Asignar/promover rol                 Sí                 No                 No
  `admin`                                                    

  Cambiar su propio                    No                 No                 No
  rol                                                        

  Cambiar empresa                      No                 No                 No
  propia                                                     

  Consultar auditoría                  Sí                 No                 No
  global                                                     

  Consultar auditoría                  No                 Sí                 No
  de su empresa                                              

  Consultar módulos          Según acceso                 Sí                 Sí
  operativos                      soporte                    

  Administrar                          No                 Sí                 No
  configuración de                                           
  empresa                                                    
  -----------------------------------------------------------------------------

### 3.1 Permisos sugeridos como constantes

``` python
PERMISSIONS = {
    "companies.read": {"super_admin"},
    "companies.create": {"super_admin"},
    "companies.update": {"super_admin"},
    "companies.deactivate": {"super_admin"},

    "users.read_global": {"super_admin"},
    "users.create_global": {"super_admin"},
    "users.read_company": {"admin"},
    "users.create_company": {"admin"},
    "users.update_company": {"admin"},
    "users.deactivate_company": {"admin"},

    "profile.read_own": {"super_admin", "admin", "user"},
    "profile.update_own": {"super_admin", "admin", "user"},
    "profile.change_password": {"super_admin", "admin", "user"},

    "audit.read_global": {"super_admin"},
    "audit.read_company": {"admin"},
}
```

Los permisos de licitaciones, bóveda, análisis y ofertas deben definirse
en una matriz funcional adicional. No conviene asumir que todo usuario
operativo puede borrar o aprobar cualquier recurso.

------------------------------------------------------------------------

## 4. Modelo de datos

## 4.1 Tabla `companies`

Campos propuestos:

  Campo              Tipo                  Reglas
  ------------------ --------------------- ------------------------------------
  `id`               UUID                  PK
  `legal_name`       VARCHAR(200)          Obligatorio
  `display_name`     VARCHAR(200)          Opcional o requerido según negocio
  `tax_id`           VARCHAR(30)           Normalizado; único si corresponde
  `email`            CITEXT/VARCHAR(255)   Opcional
  `phone`            VARCHAR(40)           Opcional
  `address`          TEXT                  Opcional
  `status`           ENUM                  `active`, `inactive`, `suspended`
  `created_at`       TIMESTAMPTZ           Obligatorio
  `updated_at`       TIMESTAMPTZ           Obligatorio
  `deactivated_at`   TIMESTAMPTZ           Nullable

Reglas: - No borrar físicamente una empresa que tenga documentos,
licitaciones o auditoría. - Desactivar/suspender bloquea autenticación y
operaciones de sus usuarios. - El identificador tributario debe
normalizarse antes de comparar. - El alta de empresa y su primer
administrador debe ser una operación transaccional o un flujo
controlado.

## 4.2 Tabla `users`

  Campo                     Tipo           Reglas
  ------------------------- -------------- -------------------------------------------
  `id`                      UUID           PK
  `company_id`              UUID           FK nullable solo para super_admin
  `email`                   VARCHAR(255)   Normalizado a minúsculas, único
  `first_name`              VARCHAR(100)   Obligatorio
  `last_name`               VARCHAR(100)   Obligatorio
  `password_hash`           TEXT           Argon2id
  `role`                    ENUM           `super_admin`, `admin`, `user`
  `status`                  ENUM           `active`, `inactive`, `locked`, `invited`
  `must_change_password`    BOOLEAN        Default según flujo
  `failed_login_attempts`   INTEGER        Default 0
  `locked_until`            TIMESTAMPTZ    Nullable
  `last_login_at`           TIMESTAMPTZ    Nullable
  `created_at`              TIMESTAMPTZ    Obligatorio
  `updated_at`              TIMESTAMPTZ    Obligatorio
  `deactivated_at`          TIMESTAMPTZ    Nullable

### Constraint de rol y empresa

``` sql
CHECK (
  (role = 'super_admin' AND company_id IS NULL)
  OR
  (role IN ('admin', 'user') AND company_id IS NOT NULL)
)
```

### Unicidad de email

La política más sencilla para el producto es email único global,
normalizado a minúsculas. Si en el futuro se desea permitir el mismo
correo en empresas distintas, se debe rediseñar el identificador de
inicio de sesión y el flujo de selección de empresa. No cambiar esta
regla sin definir antes la experiencia de login.

## 4.3 Tabla `refresh_tokens`

Campos: - `id` UUID. - `user_id` FK. - `token_hash` único. - `family_id`
UUID para agrupar rotaciones. - `created_at`, `expires_at`,
`revoked_at`. - `replaced_by_id` nullable. - `user_agent` y `ip_address`
con retención y minimización. - `reuse_detected_at` nullable.

Nunca almacenar el refresh token en texto plano.

## 4.4 Tabla `audit_logs`

Campos: - `id` UUID. - `actor_user_id` nullable para eventos de
sistema. - `company_id` nullable para eventos globales. - `action` (ej.
`user.created`, `company.suspended`). - `entity_type`, `entity_id`. -
`occurred_at`. - `ip_address`, `user_agent` cuando corresponda. -
`metadata` JSONB filtrado, sin contraseñas, tokens ni secretos.

La auditoría debe ser append-only desde la aplicación. No registrar
cuerpos completos de login ni valores secretos.

------------------------------------------------------------------------

## 5. Autenticación y sesión

## 5.1 Login

`POST /api/v1/auth/login`

Body:

``` json
{
  "email": "persona@empresa.cl",
  "password": "contraseña"
}
```

Flujo: 1. Normalizar email. 2. Aplicar rate limit por IP y cuenta. 3.
Buscar usuario por email. 4. Comprobar estado de usuario y bloqueo. 5.
Comprobar estado de empresa, si el usuario pertenece a una. 6. Verificar
contraseña Argon2id. 7. Ante fallo, incrementar contador y aplicar
bloqueo progresivo. 8. Ante éxito, resetear contador y actualizar
`last_login_at`. 9. Emitir access token corto. 10. Crear refresh token
aleatorio, guardar solo su hash y enviarlo en cookie HttpOnly. 11.
Registrar evento de auditoría.

Respuesta JSON sugerida:

``` json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "persona@empresa.cl",
    "first_name": "Nombre",
    "last_name": "Apellido",
    "role": "admin",
    "company": {
      "id": "uuid",
      "display_name": "Empresa Demo"
    },
    "permissions": ["profile.read_own", "users.read_company"]
  }
}
```

El refresh token no debe aparecer en el JSON.

## 5.2 Access token

Claims mínimos: - `sub`: ID del usuario. - `type`: `access`. - `iat`,
`exp`. - `jti`. - Opcional: `role` y `company_id` como datos
informativos para reducir consultas, pero no deben ser la única fuente
de autorización.

Recomendación: access token de 10--15 minutos. En operaciones sensibles,
verificar estado y permisos actuales desde base de datos.

## 5.3 Refresh token

-   Generar con `secrets.token_urlsafe(64)` o entropía equivalente.
-   Guardar SHA-256 del token.
-   Enviar como cookie HttpOnly, Secure en HTTPS y SameSite apropiado.
-   En cada refresh: validar hash, expiración, revocación, usuario y
    empresa; revocar el anterior y crear uno nuevo.
-   Si se reutiliza un token ya rotado, revocar la familia completa y
    exigir nuevo login.
-   En logout, revocar token actual y limpiar cookie.

## 5.4 Cookies, CORS y CSRF

-   En producción usar HTTPS.
-   Cookie refresh con `HttpOnly`, `Secure`, `SameSite=Lax` o `Strict`
    según despliegue.
-   Si frontend y backend están en sitios distintos, revisar
    `SameSite=None; Secure` y protección CSRF.
-   CORS debe permitir solo los orígenes frontend configurados, nunca
    `*` junto con credenciales.
-   El refresh/logout basado en cookie debe protegerse contra CSRF
    mediante estrategia adecuada (token CSRF, Origin/Referer y política
    SameSite).
-   En desarrollo local, documentar diferencias sin relajar producción.

## 5.5 Logout

`POST /api/v1/auth/logout`

-   Revoca refresh token actual.
-   Limpia cookie.
-   Frontend elimina access token de memoria y datos privados de caché.
-   Respuesta idempotente.

## 5.6 Sesión actual

`GET /api/v1/auth/me`

Devuelve: - datos básicos del usuario; - rol; - empresa; - estado; -
permisos efectivos; - configuración mínima para renderizar la
aplicación.

No devuelve hash, tokens ni datos internos de seguridad.

------------------------------------------------------------------------

## 6. Perfil personal

Disponible para los tres roles.

### Vista `/app/profile`

Secciones: 1. Datos personales. 2. Datos de acceso. 3. Seguridad. 4.
Sesiones activas (si se implementa). 5. Preferencias (opcional).

### Campos editables por el propio usuario

-   Nombre.
-   Apellido.
-   Teléfono, si existe en el modelo.
-   Preferencias de interfaz, si se incorporan.

### Campos no editables por el propio usuario

-   ID.
-   Rol.
-   Empresa.
-   Estado.
-   Permisos.
-   Email de acceso, salvo flujo especial de cambio con verificación.
-   Fecha de creación y auditoría.

### Endpoints

  Método   Endpoint                         Uso
  -------- -------------------------------- -------------------------------------
  GET      `/api/v1/auth/me`                Obtener perfil actual
  PATCH    `/api/v1/auth/me`                Editar campos personales permitidos
  POST     `/api/v1/auth/change-password`   Cambiar contraseña
  GET      `/api/v1/auth/sessions`          Listar sesiones, si se implementa
  DELETE   `/api/v1/auth/sessions/{id}`     Revocar una sesión propia

### Cambio de contraseña

Body:

``` json
{
  "current_password": "actual",
  "new_password": "nueva contraseña segura"
}
```

Validar contraseña actual, política de complejidad razonable y que la
nueva no sea igual a la anterior. Al cambiarla, revocar refresh tokens
existentes y emitir una nueva sesión o solicitar login nuevamente.
Registrar evento.

------------------------------------------------------------------------

## 7. Administración de empresas --- `super_admin`

### Vista `/platform/companies`

Tabla: - Nombre legal. - Nombre visible. - RUT/identificador. -
Estado. - Cantidad de usuarios. - Fecha de creación. - Acciones.

Filtros: - Texto. - Estado. - Fecha. - Paginación.

### Vista `/platform/companies/new`

Formulario: - Nombre legal. - Nombre visible. - RUT/identificador
tributario. - Email de contacto. - Teléfono. - Dirección. - Estado
inicial. - Datos del primer administrador (nombre, apellido, email).

Se recomienda crear empresa y primer administrador en un flujo
transaccional. La contraseña inicial debe establecerse mediante
invitación o contraseña temporal de un solo uso; evitar enviar
contraseñas permanentes por correo.

### Vista `/platform/companies/:id`

Pestañas: - Resumen. - Datos de empresa. - Usuarios. -
Actividad/auditoría. - Estado y acciones.

### Editar empresa

Permitir editar datos de contacto y razón social según política. Cambios
de identificador tributario deben tener validación especial y auditoría.

### Desactivar/suspender empresa

-   Confirmación explícita.
-   Solicitar motivo.
-   Revocar sesiones activas de sus usuarios.
-   Impedir login y operaciones nuevas.
-   Conservar información y auditoría.
-   Permitir reactivación por `super_admin`.

### Endpoints

  -------------------------------------------------------------------------------------------
  Método                  Endpoint                                    Descripción
  ----------------------- ------------------------------------------- -----------------------
  GET                     `/api/v1/companies`                         Listar empresas, solo
                                                                      super_admin

  POST                    `/api/v1/companies`                         Crear empresa

  GET                     `/api/v1/companies/{company_id}`            Ver empresa

  PATCH                   `/api/v1/companies/{company_id}`            Editar empresa

  POST                    `/api/v1/companies/{company_id}/suspend`    Suspender empresa

  POST                    `/api/v1/companies/{company_id}/activate`   Reactivar empresa

  GET                     `/api/v1/companies/{company_id}/users`      Usuarios de empresa

  POST                    `/api/v1/companies/{company_id}/users`      Crear usuario en
                                                                      empresa
  -------------------------------------------------------------------------------------------

El backend debe validar que el `company_id` de la ruta exista. El
permiso global se verifica antes de ejecutar la operación.

------------------------------------------------------------------------

## 8. Administración de usuarios --- `super_admin`

### Vista `/platform/users`

Lista global con: - Nombre. - Email. - Empresa. - Rol. - Estado. -
Último acceso. - Fecha de creación. - Acciones.

Filtros por empresa, rol, estado y texto.

### Crear usuario global

`super_admin` puede: - Crear un `admin` para una empresa. - Crear un
`user` para una empresa. - Crear otro `super_admin` solo mediante
procedimiento restringido, con auditoría reforzada y confirmación
adicional.

No permitir `super_admin` con `company_id` asignado ni roles de empresa
con `company_id = NULL`.

### Editar usuario

Puede modificar: - Nombre y apellido. - Rol, dentro de las reglas. -
Empresa, solo mediante transferencia controlada. - Estado. - Requerir
restablecimiento de contraseña.

La transferencia de empresa debe: 1. Validar que el nuevo destino esté
activo. 2. Revocar refresh tokens. 3. Auditar origen y destino. 4.
Revisar recursos propiedad del usuario: los recursos de empresa no se
transfieren automáticamente. 5. No cambiar el `company_id` de los
recursos históricos.

### Endpoints

  --------------------------------------------------------------------------------------------
  Método                  Endpoint                                     Descripción
  ----------------------- -------------------------------------------- -----------------------
  GET                     `/api/v1/users`                              Listado global

  POST                    `/api/v1/users`                              Crear usuario global

  GET                     `/api/v1/users/{user_id}`                    Detalle

  PATCH                   `/api/v1/users/{user_id}`                    Editar datos permitidos

  POST                    `/api/v1/users/{user_id}/deactivate`         Desactivar

  POST                    `/api/v1/users/{user_id}/activate`           Activar

  POST                    `/api/v1/users/{user_id}/reset-password`     Iniciar
                                                                       restablecimiento

  POST                    `/api/v1/users/{user_id}/revoke-sessions`    Revocar sesiones

  POST                    `/api/v1/users/{user_id}/transfer-company`   Transferencia
                                                                       controlada
  --------------------------------------------------------------------------------------------

No se debe ofrecer un endpoint genérico que permita cambiar
arbitrariamente `role`, `company_id` y `status` sin reglas.

------------------------------------------------------------------------

## 9. Administración de usuarios --- `admin`

### Vista `/app/settings/users`

El administrador solo ve usuarios cuyo `company_id` coincide con el
suyo.

Tabla: - Nombre. - Email. - Rol. - Estado. - Último acceso. - Fecha de
alta. - Acciones.

### Crear usuario

El admin puede crear usuarios con rol `user`.

Campos: - Nombre. - Apellido. - Email. - Teléfono opcional. -
Estado/invitación.

No debe recibir `company_id` desde el frontend. El servicio lo asigna
desde el usuario autenticado.

### Editar usuario

Puede editar: - Nombre. - Apellido. - Teléfono. - Estado, si tiene
permiso. - Reenvío de invitación o restablecimiento de acceso.

No puede: - Elevarse a `super_admin`. - Crear o promover admins en la
política inicial. - Cambiar empresa. - Cambiar su propio rol. - Editar
usuarios de otra empresa. - Ver tokens o hashes.

### Desactivar usuario

-   Confirmar acción y motivo opcional.
-   Revocar sesiones.
-   Conservar historial y propiedad de recursos.
-   No eliminar documentos, licitaciones ni registros creados por esa
    persona.

### Endpoints

  ---------------------------------------------------------------------------------------------------
  Método                  Endpoint                                            Descripción
  ----------------------- --------------------------------------------------- -----------------------
  GET                     `/api/v1/company/users`                             Listar usuarios de
                                                                              empresa actual

  POST                    `/api/v1/company/users`                             Crear usuario `user` en
                                                                              empresa actual

  GET                     `/api/v1/company/users/{user_id}`                   Ver usuario de su
                                                                              empresa

  PATCH                   `/api/v1/company/users/{user_id}`                   Editar campos
                                                                              permitidos

  POST                    `/api/v1/company/users/{user_id}/deactivate`        Desactivar

  POST                    `/api/v1/company/users/{user_id}/activate`          Activar

  POST                    `/api/v1/company/users/{user_id}/reset-password`    Enviar flujo de
                                                                              recuperación

  POST                    `/api/v1/company/users/{user_id}/revoke-sessions`   Revocar sesiones
  ---------------------------------------------------------------------------------------------------

**Importante:** antes de devolver o modificar un usuario, consultar por
`user_id` y `company_id` del actor. Si no pertenece a la empresa,
responder 404 para evitar revelar la existencia del usuario.

------------------------------------------------------------------------

## 10. Experiencia del usuario `user`

El usuario básico no debe quedar "flojeando" ni tener una aplicación
vacía. Su rol es operativo.

### Menú recomendado

-   Inicio.
-   Licitaciones.
-   Bóveda de empresa.
-   Análisis.
-   Chat/consultas.
-   Ofertas en preparación.
-   Mi perfil.

### Funciones operativas

Según permisos que defina el negocio, puede: - Crear licitaciones. -
Subir documentos de licitación. - Consultar licitaciones existentes. -
Ejecutar análisis Go/No-Go. - Revisar hallazgos y evidencias. - Proponer
o registrar una decisión, si tiene permiso. - Consultar documentos de
bóveda. - Subir antecedentes a la bóveda si se habilita
`vault.documents.create`. - Preparar checklist de oferta. - Seleccionar
documentos y generar una versión de carpeta de oferta. - Consultar su
historial de actividad.

### Restricciones

-   No administra usuarios.
-   No administra empresas.
-   No asigna roles.
-   No cambia configuración global.
-   No accede a auditoría administrativa.
-   No puede consultar recursos de otra empresa.
-   No puede borrar permanentemente documentos ni licitaciones.

Recomendación: separar permisos operativos de los roles. Por ejemplo,
inicialmente todos los `user` pueden crear licitaciones y ejecutar
análisis, pero solo algunos usuarios autorizados pueden confirmar el
Go/No-Go o generar la versión final de una oferta.

------------------------------------------------------------------------

## 11. Endpoints completos del módulo

Prefijo: `/api/v1`.

### Auth

  Método   Ruta                            Acceso
  -------- ------------------------------- ------------------------------
  POST     `/auth/login`                   Público con rate limit
  POST     `/auth/refresh`                 Cookie refresh válida
  POST     `/auth/logout`                  Usuario autenticado o sesión
  GET      `/auth/me`                      Todos
  PATCH    `/auth/me`                      Todos
  POST     `/auth/change-password`         Todos
  GET      `/auth/sessions`                Todos, propias
  DELETE   `/auth/sessions/{session_id}`   Todos, propias

### Empresas

  Método   Ruta                         Acceso
  -------- ---------------------------- -------------
  GET      `/companies`                 super_admin
  POST     `/companies`                 super_admin
  GET      `/companies/{id}`            super_admin
  PATCH    `/companies/{id}`            super_admin
  POST     `/companies/{id}/suspend`    super_admin
  POST     `/companies/{id}/activate`   super_admin
  GET      `/company/profile`           admin
  PATCH    `/company/profile`           admin

`/company/profile` siempre opera sobre la empresa del usuario
autenticado. No acepta `company_id`.

### Usuarios

  Método   Ruta                               Acceso
  -------- ---------------------------------- ----------------------
  GET      `/users`                           super_admin
  POST     `/users`                           super_admin
  GET      `/users/{id}`                      super_admin
  PATCH    `/users/{id}`                      super_admin
  POST     `/users/{id}/activate`             super_admin
  POST     `/users/{id}/deactivate`           super_admin
  GET      `/company/users`                   admin
  POST     `/company/users`                   admin
  GET      `/company/users/{id}`              admin, misma empresa
  PATCH    `/company/users/{id}`              admin, misma empresa
  POST     `/company/users/{id}/activate`     admin, misma empresa
  POST     `/company/users/{id}/deactivate`   admin, misma empresa

### Auditoría

  Método   Ruta                    Acceso
  -------- ----------------------- -----------------------
  GET      `/audit-logs`           super_admin
  GET      `/company/audit-logs`   admin, empresa actual

Los filtros de auditoría deben permitir rango de fechas, actor, acción y
entidad, con paginación. El usuario `user` no accede a estos endpoints
administrativos.

------------------------------------------------------------------------

## 12. Vistas frontend y navegación

## 12.1 Rutas públicas

-   `/login`
-   `/forgot-password` (cuando exista servicio de correo)
-   `/reset-password` (cuando exista servicio de correo)

## 12.2 Rutas `super_admin`

``` text
/platform
/platform/companies
/platform/companies/new
/platform/companies/:companyId
/platform/users
/platform/users/new
/platform/users/:userId
/platform/audit
/app/profile
```

### Dashboard global

-   Total de empresas activas.
-   Empresas suspendidas.
-   Total de usuarios.
-   Usuarios activos.
-   Alertas de sistema.
-   Trabajos fallidos.
-   Actividad reciente.

## 12.3 Rutas `admin`

``` text
/app
/app/profile
/app/settings
/app/settings/company
/app/settings/users
/app/settings/users/new
/app/settings/users/:userId
/app/settings/audit
/app/vault
/app/tenders
/app/analysis
/app/chat
/app/offers
```

### Dashboard admin

-   Actividad y métricas de la empresa.
-   Próximos cierres.
-   Documentos por vencer.
-   Usuarios activos.
-   Análisis por revisar.
-   Ofertas en preparación.

## 12.4 Rutas `user`

``` text
/app
/app/profile
/app/vault
/app/tenders
/app/tenders/new
/app/tenders/:tenderId
/app/analysis
/app/chat
/app/offers
```

El menú se construye a partir de permisos efectivos. Las rutas deben
tener guard de sesión y permiso, pero la API vuelve a validar todo.

------------------------------------------------------------------------

## 13. Contratos de request/response

### 13.1 Crear empresa

`POST /api/v1/companies`

``` json
{
  "legal_name": "Servicios Ejemplo SpA",
  "display_name": "Servicios Ejemplo",
  "tax_id": "76.123.456-7",
  "email": "contacto@ejemplo.cl",
  "phone": "+56 9 1234 5678",
  "address": "Santiago, Chile",
  "initial_admin": {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": "ana@ejemplo.cl"
  }
}
```

No aceptar `status`, `company_id` ni `role` arbitrarios del cliente para
el administrador inicial. El servicio crea la empresa activa y el primer
usuario `admin` dentro de una transacción, sujeto a la política de
invitación.

### 13.2 Crear usuario de empresa

`POST /api/v1/company/users`

``` json
{
  "first_name": "Luis",
  "last_name": "Gómez",
  "email": "luis@ejemplo.cl"
}
```

El backend asigna: - `company_id = current_user.company_id` -
`role = user` - `status = invited` o `active`, según el flujo de
invitación.

No aceptar `role` ni `company_id` del body.

### 13.3 Editar perfil propio

`PATCH /api/v1/auth/me`

``` json
{
  "first_name": "Luis Alberto",
  "last_name": "Gómez"
}
```

Usar un schema allowlist. Cualquier campo extra como `role`,
`company_id`, `status` debe rechazarse o ignorarse de manera explícita y
segura.

### 13.4 Editar usuario de empresa

`PATCH /api/v1/company/users/{user_id}`

``` json
{
  "first_name": "Luis Alberto",
  "last_name": "Gómez"
}
```

El admin no envía la empresa ni el rol. La consulta se limita al
`company_id` de la sesión.

------------------------------------------------------------------------

## 14. Arquitectura backend sugerida

``` text
backend/app/
  api/
    dependencies/
      auth.py
      permissions.py
      database.py
    v1/
      auth.py
      companies.py
      users.py
      audit.py
  core/
    config.py
    security.py
    permissions.py
    exceptions.py
  db/
    base.py
    session.py
  models/
    company.py
    user.py
    refresh_token.py
    audit_log.py
  schemas/
    auth.py
    user.py
    company.py
    common.py
  repositories/
    user_repository.py
    company_repository.py
    refresh_token_repository.py
    audit_repository.py
  services/
    auth_service.py
    user_service.py
    company_service.py
    audit_service.py
```

### Responsabilidades

-   Router: valida HTTP y delega.
-   Dependency: obtiene sesión y usuario autenticado.
-   Permission dependency: valida rol/permisos.
-   Service: aplica reglas y transacciones.
-   Repository: ejecuta consultas con filtros de empresa.
-   Model: representa persistencia.
-   Schema: controla qué campos entran y salen.

No colocar toda la lógica en los routers.

------------------------------------------------------------------------

## 15. Dependencias de autorización

### Usuario actual

Una dependencia `get_current_user` debe: 1. Extraer Bearer access token.
2. Verificar firma, algoritmo, expiración y tipo. 3. Obtener `sub`. 4.
Consultar el usuario y validar que esté activo. 5. Validar que su
empresa esté activa, cuando corresponda. 6. Retornar un objeto de
usuario confiable.

### Permiso requerido

Una dependencia como `require_roles(...)` o `require_permission(...)`
protege cada endpoint.

Ejemplo conceptual:

``` python
@router.post("/companies")
async def create_company(
    payload: CompanyCreate,
    current_user: User = Depends(require_roles("super_admin")),
):
    ...
```

En endpoints de empresa: - El `company_id` se deriva de
`current_user.company_id`. - Las consultas por ID deben filtrar también
por empresa. - No hacer primero una búsqueda global por UUID y confiar
en que el frontend no lo manipulará.

### Defensa adicional: PostgreSQL RLS

Se puede incorporar Row Level Security para tablas multi-tenant: -
establecer el `company_id` en el contexto de transacción; - políticas
RLS para SELECT/INSERT/UPDATE/DELETE; - limpiar contexto al terminar
transacción; - tratar `super_admin` con un camino explícito y auditado.

RLS es defensa adicional; no sustituye la autorización de aplicación.
Debe probarse cuidadosamente con pool de conexiones para evitar que el
contexto de una petición se filtre a otra.

------------------------------------------------------------------------

## 16. Seguridad y amenazas a cubrir

### IDOR / acceso cruzado

Un usuario no debe acceder a `/documents/{uuid}` de otra empresa. Cada
consulta debe validar `company_id` en la misma operación de base de
datos.

### Escalada de privilegios

-   Schemas separados para crear, editar perfil y administrar usuarios.
-   Nunca usar `model_dump()` de un payload general para actualizar
    campos protegidos.
-   No confiar en rol o empresa incluidos en JWT sin comprobar estado
    actual para operaciones sensibles.
-   Prohibir que admin cree/promueva admins en la política inicial.

### Fuerza bruta

-   Rate limit por IP y cuenta.
-   Bloqueo progresivo con expiración.
-   Respuesta de login genérica para no enumerar cuentas.
-   Registrar intentos fallidos sin guardar contraseñas.

### Robo/reutilización de refresh

-   Hash de refresh en DB.
-   Rotación.
-   Detección de reutilización.
-   Revocación de familia.
-   Cookies seguras.
-   Revocar sesiones al desactivar usuario o empresa.

### CSRF / CORS / XSS

-   Estrategia CSRF en endpoints que usan cookies.
-   CORS por allowlist.
-   No usar `dangerouslySetInnerHTML` con contenido de documentos o IA
    sin sanitización.
-   No almacenar refresh token en almacenamiento accesible por
    JavaScript.

### Auditoría

Eventos mínimos: - `auth.login.success` - `auth.login.failed` -
`auth.logout` - `auth.refresh` - `auth.refresh.reuse_detected` -
`user.created` - `user.updated` - `user.activated` -
`user.deactivated` - `user.role_changed` - `company.created` -
`company.updated` - `company.suspended` - `company.activated` -
`profile.updated` - `password.changed` - `sessions.revoked`

No registrar contraseñas, JWT completos, refresh tokens ni secretos.

------------------------------------------------------------------------

## 17. Validaciones de negocio

1.  Email normalizado antes de guardar y buscar.
2.  Email único global.
3.  `super_admin` siempre sin empresa.
4.  `admin` y `user` siempre con empresa.
5.  Empresa inactiva/suspendida no permite login de sus miembros.
6.  Admin solo lista usuarios de su empresa.
7.  Admin solo crea rol `user`.
8.  User no administra cuentas.
9.  Un usuario no puede cambiar su rol desde perfil.
10. Un usuario no puede cambiar su empresa desde perfil.
11. Desactivar usuario revoca sus sesiones.
12. Desactivar empresa revoca las sesiones de sus usuarios.
13. El último admin activo de una empresa no debe poder desactivarse sin
    reemplazo o confirmación de un super_admin.
14. No eliminar físicamente empresas/usuarios con historial dependiente.
15. Toda acción administrativa relevante crea un audit log.

------------------------------------------------------------------------

## 18. Pruebas obligatorias

### Autenticación

-   Login correcto.
-   Password incorrecta.
-   Usuario inexistente con respuesta genérica.
-   Usuario inactivo.
-   Empresa suspendida.
-   Cuenta bloqueada.
-   Refresh válido.
-   Refresh expirado.
-   Refresh revocado.
-   Reutilización de refresh anterior.
-   Logout.
-   Cambio de contraseña revoca sesiones.

### RBAC

-   `user` recibe 403 al crear usuarios.
-   `admin` recibe 403 al crear empresas.
-   `admin` no puede asignar rol admin.
-   `super_admin` puede crear empresa.
-   Perfil no permite cambiar `role`, `company_id` o `status`.

### Multi-tenancy

-   Admin A no lista usuarios de B.
-   Admin A no consulta usuario de B por UUID.
-   Admin A no edita ni desactiva usuario de B.
-   User A no descarga documentos de B.
-   Cambiar `company_id` en body/query no amplía acceso.
-   Filtros, búsquedas, conteos y exportaciones respetan empresa.
-   Tareas asíncronas conservan el tenant correcto.

### Auditoría

-   Se registra actor, acción, fecha y entidad.
-   No se guardan secretos.
-   Los usuarios no pueden modificar registros de auditoría.

------------------------------------------------------------------------

## 19. Criterios de aceptación del módulo

El módulo queda aceptado cuando:

-   Los tres roles pueden iniciar y cerrar sesión.
-   El refresh token rota correctamente y su reutilización se detecta.
-   Los tres roles pueden editar su perfil dentro de los campos
    permitidos.
-   Los tres roles pueden cambiar su contraseña.
-   `super_admin` puede crear, editar, suspender y reactivar empresas.
-   `super_admin` puede crear y administrar usuarios de cualquier
    empresa.
-   `admin` puede listar y administrar usuarios de su empresa, creando
    solo usuarios `user`.
-   `user` dispone de panel y módulos operativos acordes a sus permisos.
-   `admin` y `user` no pueden modificar su rol ni empresa.
-   Ningún usuario de una empresa puede acceder a datos de otra.
-   Los endpoints protegidos devuelven 401 cuando no hay sesión y 403
    cuando falta permiso.
-   Las acciones administrativas y de seguridad quedan auditadas.
-   Existe cobertura automatizada de los casos críticos descritos.

------------------------------------------------------------------------

## 20. Orden de implementación recomendado

### Sprint A --- Base de identidad

1.  Configuración Pydantic Settings.
2.  SQLAlchemy async y sesión.
3.  Alembic.
4.  Modelos Company, User, RefreshToken y AuditLog.
5.  Migración inicial y constraints.
6.  Pruebas de modelos.

### Sprint B --- Autenticación

1.  Hash/verificación Argon2id.
2.  Login.
3.  Access JWT.
4.  Refresh cookie y almacenamiento hash.
5.  Rotación y detección de reutilización.
6.  Logout.
7.  `/auth/me`.
8.  Cambio de contraseña.
9.  Rate limiting y auditoría.

### Sprint C --- Administración global

1.  CRUD empresas.
2.  Alta de empresa + primer admin.
3.  Listado global de usuarios.
4.  Crear/editar/desactivar usuarios.
5.  Suspender/reactivar empresa.
6.  Revocación de sesiones.
7.  Auditoría global.

### Sprint D --- Administración de empresa

1.  Perfil/datos de empresa.
2.  Listado de usuarios de empresa.
3.  Crear usuario básico.
4.  Editar/desactivar/activar usuario.
5.  Auditoría de empresa.
6.  Pruebas de aislamiento.

### Sprint E --- Frontend

1.  Login y manejo de sesión.
2.  Layout por rol.
3.  Perfil y cambio de contraseña.
4.  Panel super_admin.
5.  CRUD de empresas.
6.  CRUD global de usuarios.
7.  Panel admin.
8.  CRUD de usuarios de empresa.
9.  Dashboard y navegación user.
10. Manejo de expiración y errores.

No avanzar a los módulos de bóveda y licitaciones hasta que las pruebas
multi-tenant del módulo de identidad estén pasando.

------------------------------------------------------------------------

## 21. Decisiones que deben confirmarse

-   ¿Email único global o único por empresa? Se recomienda global para
    este diseño.
-   ¿Admin puede crear otros admins? Política inicial: no; solo
    super_admin.
-   ¿El alta se hace con invitación por correo o contraseña temporal?
-   ¿Se permite que una persona pertenezca a más de una empresa? Este
    diseño inicial asume una cuenta = una empresa, salvo super_admin.
-   ¿Se requiere MFA para super_admin? Recomendado para producción.
-   ¿Cuánto tiempo se conserva auditoría y sesiones revocadas?
-   ¿Qué permisos operativos exactos tendrá `user` para crear, editar,
    aprobar y generar ofertas?

**Recomendación final:** implementar primero este módulo como una unidad
vertical completa ---base de datos, API, pruebas y vistas--- y no solo
como una pantalla de login. La autenticación identifica al usuario; RBAC
define qué puede hacer; multi-tenancy define sobre qué datos puede
hacerlo. Las tres capas deben funcionar juntas desde el primer sprint.
