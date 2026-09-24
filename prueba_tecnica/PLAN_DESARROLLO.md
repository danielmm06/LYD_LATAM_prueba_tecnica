# Plan de desarrollo — Módulo Odoo 19 `lyd_sale_record` (Prueba técnica LYD LATAM) — v3

> **Estado: decisiones cerradas.** Falta tu visto bueno final a este plan para empezar las Fases 0 y 1. El tiempo real (sección 8) necesita además tu aprobación explícita.
> Requisitos: `PRUEBA_TECNICA.md`. Reglas y evidencias: `REGLAS_DESARROLLO.md` (citadas como **[R§n]**).
> Todas las APIs de este plan se comprobaron en el código fuente local de Odoo 19.

---

## 1. Decisiones

### 1.1 Aprobadas

| # | Decisión | Qué implica en el plan |
|---|---|---|
| **D1** | Módulo `lyd_sale_record` | Modelo `lyd.sale.record`, wizard `lyd.sale.record.import`, XML IDs `lyd_sale_record_*`. |
| **D2** | Cliente, vendedor y producto **relacionados con los modelos de Odoo**; si no existen, **se crean** | `partner_id → res.partner`, `user_id → res.users` (interno), `product_id → product.product`, igual que `sale.order` / `sale.order.line` [R§4 bis]. Nueva dependencia `product` (arrastra `mail` y `uom`). Ver N1 y N2. |
| **D3** | Estado: `draft` → "Borrador", `confirmed` → "Confirmada", `cancelled` → "Cancelada". El texto del Excel se **normaliza solo con `lower()` + `strip()`** | `Selection` con claves y etiquetas en inglés (`Draft`, `Confirmed`, `Cancelled`) traducidas en `es.po`. Diccionario mínimo de 3 entradas en español; además, un valor que ya sea una clave técnica se acepta directamente (sección 5, paso 4). |
| **D4** | No se rechaza la fila si `Valor Total ≠ Cantidad × Valor Unitario`: **se ajusta el precio unitario** | `price_unit = price_total / quantity` cuando no cuadran (comparando con la moneda). La regla vive en el **modelo**, así que aplica también a la creación manual y por API (sección 4.3). Ver N3. |
| **D6** | `js_class` + subclase de `ListController` | Sin efectos globales en otras listas. |
| **D7** | Tablero = acción de ventana con graph + pivot + lista con tarjetas KPI | Patrón nativo de `purchase_dashboard_list`. |
| **D8** | KPI del mes actual **y** del filtro activo | 4 tarjetas (sección 6.3). |
| **D11** | Solo `.xlsx`. Cualquier otro formato → `UserError` | Texto fuente en inglés: *"Unsupported format. Please upload a file with the .xlsx extension."*; en `es.po`: *"Formato no soportado. Por favor, cargue un archivo con extensión .xlsx"* [R§1.3]. |
| **D15** | No se crea `CLAUDE.md` | Las reglas viven en `REGLAS_DESARROLLO.md`. |

### 1.2 Adoptadas por defecto (sin objeción)

| # | Decisión | Recomendación |
|---|---|---|
| **D5** | Importación todo o nada | **Sí.** Si una fila falla no se crea nada: ni ventas, ni clientes, ni vendedores, ni productos, porque todo va en la misma transacción y el `UserError` la revierte. |
| **D9** | Grupos propios `lyd_sale_record_group_user` / `_manager` | **Sí.** El grupo *user* es además el canal del bus. |
| **D10** | Throttle de 2 s | **Sí.** |
| **D12** | Importes | `price_total`: `Monetary` en la moneda de la compañía. `price_unit`: **`Float(min_display_digits='Product Price')`, como `sale.order.line`** (cambia respecto a la v1): guarda `total / cantidad` sin truncar [R§4]. |
| **D13** | Cantidad | `Float(digits='Product Unit')`, como `sale.order.line.product_uom_qty` [R§4]. |
| **D14** | Idioma de prueba `es_CO` | Con un único `i18n/es.po` basta. |
| **D16** | Sin detección de reimportaciones | Solo trazabilidad con `import_file_name`. |

### 1.3 Aprobadas en esta ronda (salen de D2 y D4)

| # | Decisión | Qué implica en el plan |
|---|---|---|
| **N1** | Crear clientes, vendedores y productos con `sudo()` **solo** en tres métodos privados del wizard | `_find_or_create_partner/_user/_product` escriben únicamente `name` (y `login` en usuarios). El importador no gana permisos en el resto de Odoo. Un usuario interno normal no tiene permiso para crearlos [R§4 bis]. |
| **N2** | Vendedor nuevo = usuario interno sin contraseña con `login` generado (`juan.perez`, `.2`, `.3`…). **Siempre se valida si el usuario existe antes de crearlo** | Validación en dos pasos (sección 5, paso 7). **Incluye los usuarios archivados** (`active_test=False`): `UNIQUE (login)` es una restricción de base de datos que también los cuenta (`odoo/addons/base/models/res_users.py:227, 274`). Si solo existe archivado, se reutiliza en lugar de crear un duplicado. Aviso de licencia en el README. |
| **N3** | Campo `price_unit_adjusted` + contador en el mensaje final | Filtro "Unit price adjusted" en la búsqueda. |
| **N4** | Valor unitario vacío → `price_total / quantity`, marcado como ajustado | Regla del modelo (sección 4.3). |

> **Nota (refactor de rendimiento y DRY, aprobado por el Tech Lead):** los métodos `_find_or_create_partner/_user/_product` citados en N1 ya no existen. Los sustituye `_get_or_create_records()`, que busca los nombres únicos del Excel en una consulta por modelo (en lotes de `SEARCH_BATCH_SIZE = 500`) y crea los que faltan con un solo `sudo().create()` por modelo. La regla de N1 no cambia: el `sudo()` sigue limitado al asistente y solo escribe `name` (y `login` en los usuarios, que ahora se generan con `_generate_user_logins()` en una sola consulta). N2 se mantiene: la búsqueda incluye los usuarios archivados antes de crear ninguno.

---

## 2. Estructura del entregable

```
prueba_tecnica/                          ← entra en addons_path
├── REGLAS_DESARROLLO.md
├── PLAN_DESARROLLO.md
├── PRUEBA_TECNICA.md
├── sample_data/
│   ├── generate_sample_data.py          (script openpyxl que genera los dos .xlsx)
│   ├── sales_sample.xlsx
│   └── sales_sample_with_errors.xlsx
└── lyd_sale_record/
    ├── __init__.py
    ├── __manifest__.py
    ├── README.md
    ├── i18n/{lyd_sale_record.pot, es.po}
    ├── models/{__init__.py, lyd_sale_record.py}
    ├── wizard/{__init__.py, lyd_sale_record_import.py, lyd_sale_record_import_views.xml}
    ├── security/{lyd_sale_record_groups.xml, lyd_sale_record_security.xml, ir.model.access.csv}
    ├── views/{lyd_sale_record_views.xml, lyd_sale_record_menus.xml}
    ├── static/description/icon.png
    ├── static/src/views/realtime_list/{realtime_list_controller.js, realtime_list_view.js}
    ├── static/src/views/sale_record_dashboard/{sale_record_dashboard.js, .xml, .scss}
    └── tests/{__init__.py, common.py, test_lyd_sale_record.py,
               test_lyd_sale_record_import.py, test_bus_notification.py}
```

---

## 3. Fase 0 — Entorno

1. Crear `configs/lyd_prueba.cfg` a partir de `configs/demos.cfg`, con estos cambios:
   - `addons_path = ./, ./addons, ./custom_addons/LYD_LATAM_prueba_tecnica/prueba_tecnica`.
   - `db_name = lyd_prueba`, `dbfilter = ^lyd_prueba$`.
   - Eliminar `server_wide_modules = web,queue_job` (el valor por defecto de v19 es `base,rpc,web`, `odoo/tools/config.py:30`; `queue_job` no está en este `addons_path`).
   - `workers = 0` [R§2].
2. Base de datos `lyd_prueba` sin datos de demostración y con `es_CO` activo.

**Criterio de salida:** el servidor arranca con el `.cfg` nuevo.

---

## 4. Fase 1 — Esqueleto, modelo y seguridad

### 4.1 `__manifest__.py`
`version='19.0.1.0.0'`, `license='LGPL-3'`, `depends=['base', 'web', 'bus', 'product']`, `external_dependencies={'python': ['openpyxl']}`, `data` en orden (grupos → ACL → reglas → vistas → wizard → menús), `assets` en `web.assets_backend`, `application=True` [R§3].

### 4.2 Modelo `lyd.sale.record` (`_description = 'Sale Record'`, `_order = 'date desc, id desc'`)

| Campo | Tipo | Atributos | Columna Excel |
|---|---|---|---|
| `date` | `Date` | `required`, `index` | Fecha |
| `partner_id` | `Many2one('res.partner')` | `string='Customer'`, `required`, `index`, `ondelete='restrict'`, `check_company=True` | Cliente |
| `user_id` | `Many2one('res.users')` | `string='Salesperson'`, `required`, `index`, `ondelete='restrict'`, `domain=[('share', '=', False)]` | Vendedor |
| `product_id` | `Many2one('product.product')` | `string='Product'`, `required`, `index`, `ondelete='restrict'`, `check_company=True` | Producto |
| `quantity` | `Float(digits='Product Unit')` | `required` | Cantidad |
| `price_unit` | `Float(min_display_digits='Product Price')` | `required`, `aggregator='avg'` | Valor Unitario |
| `price_total` | `Monetary` | `required` (suma por defecto) | Valor Total |
| `price_unit_adjusted` | `Boolean` | `readonly` (N3) | — |
| `state` | `Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')])` | `required`, `index`, `default='draft'` | Estado |
| `company_id` | `Many2one('res.company')` | `required`, `index`, `default=lambda self: self.env.company` | — |
| `currency_id` | `Many2one(related='company_id.currency_id')` | — | — |
| `import_file_name` | `Char` | `readonly` | (archivo de origen) |

- Restricciones SQL [R§4]:
  - `_quantity_positive = models.Constraint('CHECK (quantity > 0)', "The quantity must be greater than zero.")`
  - `_price_total_positive = models.Constraint('CHECK (price_total > 0)', "The total amount must be greater than zero.")`
- `_compute_display_name`: `"<cliente> - <producto> (<fecha>)"`.

### 4.3 Regla D4 en el modelo (única fuente de verdad)
- `_prepare_price_unit(vals, record=None)` (privado): con la cantidad, el precio unitario y el total finales (los de `vals` o, en `write`, los del registro), si `currency.compare_amounts(quantity * price_unit, price_total) != 0` o no hay precio unitario (N4), fija `price_unit = price_total / quantity` y `price_unit_adjusted = True`. Si cuadran, `price_unit_adjusted = False`.
- Se llama en `create` (por cada `vals` de `vals_list`) y en `write` cuando cambian `quantity`, `price_unit` o `price_total`.
- `@api.onchange('quantity', 'price_unit', 'price_total')` en el formulario para que el usuario vea el ajuste antes de guardar.
- Se compara con la moneda (`compare_amounts`), nunca con `==` [R§4].

### 4.4 Seguridad
- `lyd_sale_record_groups.xml`: `res.groups.privilege` + `lyd_sale_record_group_user` (implica `base.group_user`) + `lyd_sale_record_group_manager` (implica *user*; `user_ids` = `base.user_root` y `base.user_admin`, como `sales_team`).
- `lyd_sale_record_security.xml`: regla multicompañía `lyd_sale_record_rule_company` con `[('company_id', 'in', company_ids)]` (como `sale_order_comp_rule`, `addons/sale/security/ir_rules.xml:5-8`).
- `ir.model.access.csv`: `lyd.sale.record` (user r/w/c, manager r/w/c/u) y `lyd.sale.record.import` (user r/w/c) [R§5].

**Criterio de salida:** instala sin WARNING. Tests: cantidad o total ≤ 0 fallan; obligatorios vacíos fallan; ajuste de `price_unit` en `create` y en `write` (cuadra, no cuadra, vacío); un usuario sin grupo recibe `AccessError`.

---

## 5. Fase 2 — Wizard `lyd.sale.record.import`

Campos: `file` (`Binary`, `required`, `attachment=False`), `file_name` (`Char`).

`action_import()` (pública, `ensure_one`):

1. **Formato (D11):** si `file_name` no termina en `.xlsx` (sin distinguir mayúsculas) → `UserError(self.env._("Unsupported format. Please upload a file with the .xlsx extension."))`.
2. **Apertura:** `openpyxl.load_workbook(io.BytesIO(base64.b64decode(self.file)), data_only=True, read_only=True)` en `try/except (zipfile.BadZipFile, InvalidFileException, KeyError, ValueError)` → `UserError` "the file could not be read" (p. ej. un `.xlsx` renombrado o corrupto) [R§2]. Primera hoja.
3. **Cabecera:** normalizada con el mismo criterio que D3: `str(valor).strip().lower()`. Tiene que contener las 8 columnas de la constante `EXCEL_COLUMNS` (en cualquier orden). Si falta alguna → `UserError` con cuáles. Si no hay filas de datos → `UserError`.
4. **Estados (D3)**: normalización `str(valor).strip().lower()` y diccionario mínimo:
   ```python
   STATE_MAPPING = {'borrador': 'draft', 'confirmada': 'confirmed', 'cancelada': 'cancelled'}

   def _parse_state(self, raw_value):
       value = str(raw_value).strip().lower()
       selection_keys = dict(self.env['lyd.sale.record']._fields['state'].selection)
       return STATE_MAPPING.get(value) or (value if value in selection_keys else False)
   ```
   Acepta `Confirmada`, `CONFIRMADA`, ` confirmada ` y las claves técnicas `confirmed`, etc. Si devuelve `False`, es un error de fila que lista los valores admitidos.
5. **Validación por fila** (desde la 2; las filas totalmente vacías se omiten). Errores acumulados como `Row %(row)s, column "%(column)s": %(reason)s`:
   - Celda con `TYPE_ERROR` → error.
   - **Fecha:** `datetime`/`date` o texto `YYYY-MM-DD` (`fields.Date.to_date`); si no, error.
   - **Cliente, Vendedor, Producto:** texto no vacío tras normalizar.
   - **Cantidad, Valor Total:** numéricos y `> 0`.
   - **Valor Unitario:** numérico si viene; si está vacío, aplica N4.
   - **Estado:** vacío → error; si no, `STATE_MAPPING`.
6. Si hay errores → `UserError` con el total y los primeros 50 (más "…and %(count)s more"). **No se crea nada** (D5).
7. **Resolución de relaciones (D2, N1, N2)**, solo si no hubo errores, **por nombre único** (con caché por importación):
   - `_find_or_create_partner(name)`: `res.partner` con `[('name', '=ilike', name)] + _check_company_domain(company)`, `limit=1`; si no existe → `sudo().create({'name': name})`.
   - `_find_or_create_user(name)` (N2). **Siempre valida la existencia antes de crear:**
     1. Busca un usuario interno por nombre: `res.users.with_context(active_test=False)` con `[('name', '=ilike', name), ('share', '=', False)]`, `order='active desc, id'`, `limit=1`. Tiene prioridad el activo; si solo hay uno archivado, se reutiliza.
     2. Si no existe, genera el `login` en el formato aprobado en N2: `name.strip().lower()`, espacios → `.`, sin tildes con el helper del core `odoo.tools.remove_accents` (`odoo/tools/misc.py:713`). Odoo no prohíbe las tildes en el login, pero un login ASCII es más fácil de escribir y comprueba que esté libre **también entre los archivados** (`with_context(active_test=False).search_count([('login', '=', login)])`). Si está ocupado, prueba `.2`, `.3`…
     3. Solo entonces `sudo().create({'name': name, 'login': login})`.
   - `_find_or_create_product(name)`: `product.product` con `[('name', '=ilike', name)] + _check_company_domain(company)`, `limit=1`; si no existe → `sudo().create({'name': name})`.
   - `=ilike` sin comodines = igualdad exacta sin distinguir mayúsculas, el mismo criterio que usa el core al importar facturas [R§4 bis].
   - Cuenta cuántos registros de cada tipo se crearon, para el mensaje final.
   - > **Nota:** tras el refactor de rendimiento, estos tres métodos se sustituyeron por `_get_or_create_records()` (búsqueda por lotes de los nombres únicos y un solo `create()` por modelo). Los criterios de búsqueda de este paso no cambian. Ver la nota de la sección 1 (N1).
8. **Creación:** un solo `create(vals_list)` → la regla D4 se aplica en el modelo → **una sola** notificación de bus.
9. **Resultado:** `display_notification` (`success`): *"%(count)s sale records imported. New customers: %(partners)s, salespeople: %(users)s, products: %(products)s. Unit price adjusted in %(adjusted)s rows."*, con `next` = acción de la lista [R§6].

Vista: diálogo (`target='new'`) con `<field name="file" filename="file_name" options="{'accepted_file_extensions': '.xlsx'}"/>`, botón "Import" (`action_import`) y "Cancel". `accepted_file_extensions` solo filtra el selector de archivos del navegador; la validación real es el paso 1.

**Criterio de salida:** tests en verde:
- Archivo válido; `.xls`, `.csv` y `.pdf` → mensaje D11 exacto.
- Archivo corrupto; cabecera incompleta; sin datos.
- Fecha inválida; cada obligatorio vacío; cantidad y total 0 y negativos; texto no numérico; celda de error.
- Estado en español y como clave técnica, con mayúsculas y con espacios; estado desconocido.
- Cliente, vendedor y producto existentes (se reutilizan, sin importar mayúsculas) o nuevos (se crean una sola vez aunque aparezcan en varias filas).
- Vendedor existente activo, existente archivado (se reutiliza, no se duplica) y nuevo.
- `login` ocupado por un usuario activo o archivado → sufijo `.2`.
- Ajuste de precio (D4/N3/N4).
- Con un error no se crea **ningún** registro, tampoco clientes, vendedores ni productos.
- Un usuario con solo el grupo *user* puede importar y crear relacionados (N1).

---

## 6. Fase 3 — Vistas y tablero

### 6.1 Vistas
- **Lista** `<list js_class="lyd_sale_record_realtime_list">`: `date`, `partner_id`, `user_id` (`widget="many2one_avatar_user"`), `product_id`, `quantity`, `price_unit`, `price_total` (`sum`), `state` (`widget="badge"`), `price_unit_adjusted` (opcional), `company_id` (`groups="base.group_multi_company"`).
- **Formulario**: `<sheet>` con los datos de la venta, los importes y la información de importación (`import_file_name`, `price_unit_adjusted` solo lectura).
- **Búsqueda**: `partner_id`, `user_id`, `product_id`, `state`; filtro de fecha `date`; filtros por estado y "Unit price adjusted"; agrupar por cliente, vendedor, producto, estado y `date:month`.
- **Graph** `type="bar"`: `user_id` × `price_total` (el conmutador nativo permite ver circular o de líneas).
- **Pivot**: filas `date` `interval="month"`, columnas `state`, medidas `price_total`, `quantity` y `__count` (contexto `pivot_measures`).

`many2one_avatar_user` está verificado: se registra en `mail` (`addons/mail/static/src/views/web/fields/many2one_avatar_user_field/many2one_avatar_user_field.js:63`), que llega como dependencia de `product`, y el core lo usa igual en `addons/sale/views/sale_order_views.xml:135`.

### 6.2 Acciones y menús

| XML ID | Detalle |
|---|---|
| `lyd_sale_record_action_dashboard` | "Sales Dashboard": `graph,pivot,list,form` |
| `lyd_sale_record_action` | "Sale Records": `list,form,graph,pivot` |
| `lyd_sale_record_import_action` | "Import Excel": wizard, `target='new'` |
| `lyd_sale_record_menu_root` → `_menu_dashboard`, `_menu_records`, `_menu_import` | Menú raíz visible para el grupo *user* |

### 6.3 Tarjetas KPI (D7, D8)
- Servidor: `get_dashboard_data(domain)` (`@api.model`, `@api.readonly`) → `_read_group([], [], ['price_total:sum', '__count'])` con (1) el `domain` activo y (2) el mes actual (`date_utils.start_of/end_of(context_today, 'month')`). Devuelve importes, conteos e `id` de moneda.
- Cliente: `SaleRecordDashboard` (`props: { list }`) → `orm.call` en `onWillStart` y `onWillUpdateProps` (patrón de `purchase_dashboard.js`). Se inserta con `t-inherit="web.ListRenderer" t-inherit-mode="primary"` antes de `div.o_list_renderer`.
- Tarjetas: **Total vendido en el mes**, **Ventas del mes**, **Total vendido (filtro activo)** y **Número de ventas (filtro activo)**. Se refrescan solas cuando el tiempo real recarga la lista.

| Requisito del PDF | Dónde |
|---|---|
| Total vendido en el mes | Tarjeta KPI + pivot `date:month` |
| Número total de ventas | Tarjeta KPI + `__count` en el pivot |
| Por vendedor / cliente / producto / estado | Graph y pivot (Many2one agrupables) |
| Gráfico de barras o circular | Graph `bar` (+ `pie` con el conmutador) |
| Vista pivot | Pivot |

**Criterio de salida:** con `sales_sample.xlsx` importado, los totales cuadran con el Excel. Test de `get_dashboard_data`.

---

## 7. Fase 4 — Notificaciones en tiempo real

> ⚠️ Por la regla 0.5 de `REGLAS_DESARROLLO.md`, **este código no se escribe hasta que apruebes la sección 8**.

### 7.1 Servidor
```python
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        self._prepare_price_unit(vals)                     # D4
    records = super().create(vals_list)
    self.env.ref('lyd_sale_record.lyd_sale_record_group_user')._bus_send(
        'lyd.sale.record/created', {'count': len(records)},
    )
    return records
```
- `res.groups` hereda de `bus.listener.mixin`; los usuarios del grupo (o de uno que lo implique) ya están suscritos a ese canal [R§7.1].
- Se envía **después del commit**; si hay rollback (D5), no se envía nada.
- Un aviso por cada `create` en lote. Payload sin datos sensibles.

### 7.2 Cliente
`RealtimeListController extends ListController`, registrado como `lyd_sale_record_realtime_list` con `{...listView, Controller: RealtimeListController, Renderer: SaleRecordDashboardRenderer}` (D6).

**Criterio de salida:** `test_bus_notification.py`:
1. `create([v1, v2, v3])` → **1** fila en `bus.bus` con el canal del grupo, `type == 'lyd.sale.record/created'` y `count == 3` (tras `self.env.cr.precommit.run()`).
2. Una importación con errores → 0 notificaciones.

Además, las pruebas manuales de la Fase 6.

---

## 8. Enfoque de ráfagas y limpieza de memoria (necesita tu aprobación)

### 8.1 Throttle con flanco inicial y final (leading + trailing), `INTERVAL = 2000 ms`

```
onRecordsCreated():                              // callback con referencia fija (bind en setup)
    if (status(this) === "destroyed") return
    pending = true
    if (timer) return                            // ya hay un flush programado: se absorbe el evento
    wait = max(0, lastReload + INTERVAL - Date.now())
    timer = browser.setTimeout(flush, wait)      // wait = 0 tras un periodo de calma → flanco inicial

flush():
    timer = null
    if (status(this) === "destroyed" || !pending) return
    if (isReloading || root.editedRecord || root.selection.length) {
        timer = browser.setTimeout(flush, INTERVAL)   // se aplaza sin perder el aviso (no hace RPC)
        return
    }
    pending = false; lastReload = Date.now(); isReloading = true
    try { await this.model.load() } finally { isReloading = false }
    // si llegaron eventos durante la carga, pending ya es true y hay otro flush programado → flanco final
```

- **Ráfaga corta** (50 avisos en 300 ms): 1 recarga inmediata + como máximo 1 al cerrar la ventana de 2 s. El último evento nunca se pierde.
- **Flujo sostenido** (1 aviso cada 0,5 s): una recarga cada 2 s mientras dure el flujo.
- **Por qué no un debounce:** el `debounce` del core reinicia el temporizador en cada llamada (`timing.js:65-79`). Con eventos cada 0,5 s y 2 s de espera, la lista no se actualizaría hasta que terminara el flujo (inanición).
- **No es polling:** solo hay un temporizador mientras existe un aviso ya recibido pendiente de aplicar. Sin eventos no hay temporizadores ni peticiones.
- **Edición o selección en curso:** recargar crea un `root` nuevo y el usuario perdería lo que está haciendo [R§7.2]. Por eso se aplaza, con un reintento local sin RPC.

### 8.2 Limpieza

```
setup():
    super.setup()
    this.busService = useService("bus_service")
    this.onRecordsCreated = this.onRecordsCreated.bind(this)
    this.busService.subscribe("lyd.sale.record/created", this.onRecordsCreated)
    onWillUnmount(() => {
        this.busService.unsubscribe("lyd.sale.record/created", this.onRecordsCreated)
        browser.clearTimeout(this.timer); this.timer = null; this.pending = false
    })
```

- `unsubscribe` es **síncrono** (`bus_service.js:227-233`). Como JS usa un solo hilo, después del unmount ningún aviso llega al callback.
- **Carrera al salir de la pantalla:**
  1. Aviso **antes** del unmount → su `flush` programado se cancela con `clearTimeout`.
  2. `model.load()` **en curso** → termina, pero la guarda `status(this) === "destroyed"` impide cualquier acción posterior, y OWL no renderiza un componente destruido.
  3. Aviso **después** → ya no hay listener.
- En OWL 2, un componente desmontado no se vuelve a montar: al volver a la lista se crea una instancia nueva, que se suscribe de nuevo y carga datos frescos.
- La conexión WebSocket y el SharedWorker pertenecen al `bus_service` global: la vista solo gestiona su listener.

---

## 9. Fase 5 — Traducciones
1. `./odoo-bin i18n export -c configs/lyd_prueba.cfg -d lyd_prueba lyd_sale_record` → `i18n/lyd_sale_record.pot` [R§1.3].
2. `i18n/es.po` con todas las entradas traducidas: campos, selección (`Draft` → "Borrador", `Confirmed` → "Confirmada", `Cancelled` → "Cancelada"), vistas, menús, acciones, grupos, restricciones, mensajes Python (incluido el de D11 con el texto exacto que pediste) y JS.
3. Comprobar la interfaz en `es_CO` y en inglés. Criterio: `es.po` sin `msgstr ""` salvo la cabecera.

---

## 10. Fase 6 — Pruebas y validación final
1. `./odoo-bin -c configs/lyd_prueba.cfg -d lyd_prueba -u lyd_sale_record --test-enable --test-tags /lyd_sale_record --stop-after-init` [R§8].
2. **Tiempo real, en manual** (dos navegadores):
   - B importa y A ve los registros sin recargar.
   - Ráfaga: 50 `create` + `commit` desde `odoo-bin shell` → como máximo 2 `web_search_read` en A.
   - Flujo sostenido: 1 cada 0,5 s durante 30 s → A se actualiza cada ~2 s.
   - Limpieza: A navega fuera de la lista → 0 peticiones de esta vista en la pestaña Red.
   - Selección en curso: la recarga se aplaza sin perder la selección.
3. Checklist de `REGLAS_DESARROLLO.md` §9.

---

## 11. Fase 7 — Entregables
1. `lyd_sale_record/README.md`: instalación, uso, decisiones (incluidas N1–N4 y el aviso de licencias de N2) y **las 4 respuestas** del requisito de tiempo real.
2. `sample_data/`: script generador + `sales_sample.xlsx` (≥ 30 filas en 2026-06 y algunas del mes actual; estados en español; al menos una fila con el total descuadrado para mostrar D4) + `sales_sample_with_errors.xlsx` (un caso por validación).
3. Documentación agéntica: `REGLAS_DESARROLLO.md`, este plan, `.claude/settings.json` + hooks, y una explicación del flujo y de la supervisión.

---

## 12. Puntos de control

| Paso | Qué | Control |
|---|---|---|
| 1 | Visto bueno final a este plan v3 | **Tu validación** |
| 2 | Fases 0 y 1 | Instala sin WARNING, tests en verde |
| 3 | Fase 2 | Tests del wizard en verde |
| 4 | Fase 3 | Revisión visual del tablero |
| 5 | Sección 8 | **Tu aprobación explícita** |
| 6 | Fase 4 | Tests del bus + pruebas manuales |
| 7 | Fases 5–7 | Entrega |

---

## 13. Refactorización Master-Detail + reporte SQL — v3 (decisiones cerradas; pendiente de la orden de ejecución)

> Referencias del core: `sale.order` / `sale.order.line` (`addons/sale/models/sale_order.py:61-235`, `addons/sale/models/sale_order_line.py:34-60`) y reportes SQL (`addons/fleet/report/fleet_report.py:150-151`, `addons/crm/report/crm_activity_report.py:84-87`, `addons/account/report/account_invoice_report.py:60-79`). Reglas: `REGLAS_DESARROLLO.md`.

### 13.1 Decisiones

| # | Estado | Decisión |
|---|---|---|
| **M1** | ✅ Aprobada | Una venta por tupla normalizada **(Fecha, Cliente, Vendedor, Estado)**. Cliente y Vendedor se normalizan con `strip().lower()`. Da igual que las filas estén seguidas o no. |
| **M2** | ✅ Aprobada | `amount_total` en la cabecera: `Monetary`, `compute`, `store=True` y suma de las líneas. |
| **M3** | ✅ Aprobada (cambia) | **Sin campos duplicados en la línea.** El análisis por producto × cliente/vendedor/estado/mes sale de un **modelo de reporte sobre una vista SQL**. |
| **M4** | Adoptada por defecto | *Ventas*: lista de cabeceras con tiempo real + tarjetas KPI, y formulario con las líneas editables. *Tablero*: graph + pivot sobre el reporte SQL. |
| **M5** | Adoptada por defecto | El aviso de tiempo real solo se envía en `lyd.sale.record.create` (venta nueva), uno por lote. |
| **M6** | ✅ Hecho por el usuario | `lyd_sale_record` tiene 0 registros (comprobado con `psql`). Se puede actualizar sin migración. |
| **M7** | ✅ Aprobada | Nombre del reporte: **`lyd.sale.record.report`** (vista `lyd_sale_record_report`, archivo `report/lyd_sale_record_report.py`). Cumple R§1.1 y el patrón `<modelo_base>.report` de la guía. |
| **M8** | ✅ Aprobada | **Vista PostgreSQL real**: `init()` + `drop_view_if_exists` + `CREATE OR REPLACE VIEW` con objetos `SQL` (patrón de `addons/fleet/report/fleet_report.py:150-151`). |

### 13.2 `lyd.sale.record` (cabecera) — `models/lyd_sale_record.py`
- Se quedan `date`, `partner_id`, `user_id`, `state`, `company_id`, `currency_id` e `import_file_name`.
- Nuevos:
  - `line_ids = fields.One2many('lyd.sale.record.line', 'order_id', string="Lines", copy=True)`
  - `amount_total = fields.Monetary(string="Total", compute='_compute_amount_total', store=True)`, con `@api.depends('line_ids.price_total')` (como `sale.order.amount_total`, `sale_order.py:235`)
- Se eliminan de la cabecera: `product_id`, `quantity`, `price_unit`, `price_total`, `price_unit_adjusted`, `_quantity_positive`, `_price_total_positive`, `_prepare_price_unit`, el `@api.onchange` y el override de `write`.
- `create()`: solo mantiene el `_bus_send` del lote (M5).
- `_compute_display_name`: `"<cliente> (<fecha>)"`.
- `get_dashboard_data(domain)`: `_read_group` de la cabecera con `['amount_total:sum', '__count']` para el mes actual y para el filtro activo. "Número de ventas" pasa a ser el número de cabeceras.

### 13.3 `lyd.sale.record.line` (detalle) — `models/lyd_sale_record_line.py` (nuevo)
- `_name = 'lyd.sale.record.line'`, `_description = 'Sale Record Line'`, `_order = 'order_id, id'`.
- `order_id = fields.Many2one('lyd.sale.record', string="Sale Record", required=True, ondelete='cascade', index=True, copy=False)`, como `sale_order_line.py:34-37`.
- `product_id`, `quantity`, `price_unit`, `price_total` y `price_unit_adjusted`, con las definiciones actuales.
- `company_id` y `currency_id`: `related='order_id.…'` **sin `store`** (no se guardan, así que no duplican información). Hacen falta para `Monetary` (`currency_id`) y para `check_company=True` en `product_id` (`company_id`).
- **Restricciones SQL trasladadas:** `_quantity_positive` (`CHECK (quantity > 0)`) y `_price_total_positive` (`CHECK (price_total > 0)`).
- **Regla D4/N3/N4 trasladada:** `_prepare_price_unit` en `create`/`write` + `@api.onchange('quantity', 'price_unit', 'price_total')`. Moneda: la de `order_id` (en `create`, a partir de `vals['order_id']`). Al crear líneas con `Command.create`, el ORM añade `order_id` a los `vals` (`odoo/orm/fields_relational.py:1015`).

### 13.4 Reporte `lyd.sale.record.report` (M7/M8) — `report/lyd_sale_record_report.py` (nuevo)
- `_name`, `_description = 'Sales Analysis Report'`, **`_auto = False`**, `_rec_name = 'date'`, `_order = 'date desc'`, como `sale_report.py:10-14`.
- Campos (todos `readonly=True`): `order_id`, `date`, `partner_id`, `user_id`, `state` (misma selección que la cabecera), `company_id`, `currency_id`, `product_id`, `quantity`, `price_unit` (`aggregator='avg'`), `price_total` (`Monetary`), `price_unit_adjusted`.
- `init()`:
  ```python
  drop_view_if_exists(self.env.cr, self._table)
  self.env.cr.execute(SQL("CREATE OR REPLACE VIEW %s AS (%s)", SQL.identifier(self._table), self._query()))
  ```
  `_query()` devuelve un `SQL`: `SELECT l.id, l.order_id, o.date, o.partner_id, o.user_id, o.state, o.company_id, c.currency_id, l.product_id, l.quantity, l.price_unit, l.price_total, l.price_unit_adjusted FROM lyd_sale_record_line l JOIN lyd_sale_record o ON o.id = l.order_id JOIN res_company c ON c.id = o.company_id`. `currency_id` sale de la compañía, igual que en la cabecera (`related='company_id.currency_id'`).
- `_depends = {'lyd.sale.record': [...], 'lyd.sale.record.line': [...], 'res.company': ['currency_id']}`, para invalidar la caché como `account_invoice_report.py:60`.
- Excepción justificada a "nunca SQL directo" (R§0.4): el ORM no tiene equivalente para definir una vista de reporte. Se usan siempre objetos `SQL` / `SQL.identifier`, nunca interpolación de texto.
- Estructura de archivos según la guía: `report/__init__.py`, `report/lyd_sale_record_report.py`, `report/lyd_sale_record_report_views.xml`, importado desde el `__init__.py` raíz.

### 13.5 Wizard `lyd.sale.record.import`
1. Validación fila a fila **sin cambios** (mismos mensajes; todo o nada).
2. **Agrupación M1:** `groups = {}` (los `dict` de Python conservan el orden de inserción) con clave `(date, partner_name.strip().lower(), user_name.strip().lower(), state)`.
3. Find-or-create sin cambios (N1/N2): cliente y vendedor **una vez por grupo**, con el nombre de la primera fila del grupo; producto por línea. Las cachés siguen igual.
4. **Una sola llamada**: `self.env['lyd.sale.record'].create(vals_list)`, donde cada `vals` incluye `'line_ids': [Command.create({...}) for row in group]` (`from odoo.fields import Command`, como `sale_order_line.py:7`). Resultado: un solo aviso de bus por importación.
5. Mensaje: *"%(orders)s sales with %(lines)s lines imported. New customers: …, salespeople: …, products: …. Unit price adjusted in %(adjusted)s lines."*, con `adjusted = len(records.line_ids.filtered('price_unit_adjusted'))`.

### 13.6 Vistas, menús, seguridad y traducciones
- **Cabecera (`views/lyd_sale_record_views.xml`):**
  - Lista `js_class="lyd_sale_record_realtime_list"`: fecha, cliente, vendedor, `amount_total` (`sum`), estado.
  - Formulario: cabecera + `<field name="line_ids"><list editable="bottom">` (producto, cantidad, precio unitario, total, ajustado) + `amount_total`.
  - Búsqueda: cliente, vendedor, estado, filtro de fecha, "Unit price adjusted" (`[('line_ids.price_unit_adjusted', '=', True)]`) y agrupaciones.
  - Se eliminan las vistas graph/pivot de la cabecera y `lyd_sale_record_action_dashboard`.
- **Reporte (`report/lyd_sale_record_report_views.xml`):**
  - `graph` (bar; `product_id` × `price_total`; el conmutador permite ver circular o de líneas).
  - `pivot` (filas `date:month`, columnas `state`, medidas `price_total`, `quantity` y `__count`).
  - `search`: cliente, vendedor, producto, estado, fecha y agrupaciones por cada uno.
  - `list` de solo lectura.
  - Acción `lyd_sale_record_report_action` ("Sales Analysis": `graph,pivot,list`).
- **Menús:** Tablero → `lyd_sale_record_report_action`; Ventas → `lyd_sale_record_action`; Importar → wizard.
- **Seguridad (`ir.model.access.csv` + `lyd_sale_record_security.xml`):**
  - `lyd.sale.record.line`: user r/w/c/u (puede quitar líneas al editar una venta) y manager r/w/c/u.
  - `lyd.sale.record.report`: user y manager **solo lectura**, como `access_sale_report_salesman`.
  - Reglas multicompañía nuevas: línea `[('order_id.company_id', 'in', company_ids)]` y reporte `[('company_id', 'in', company_ids)]`, como `addons/sale/security/ir_rules.xml:11-19`.
- **Manifest:** añadir `report/lyd_sale_record_report_views.xml` a `data` (antes de los menús) y subir la versión a `19.0.1.1.0`.
- **JS:** sin cambios. El tiempo real y las tarjetas siguen sobre la lista de cabeceras.
- **Traducciones:** regenerar el `.pot` y actualizar `es.po`: modelos nuevos, campos, acción "Sales Analysis", mensajes nuevos del wizard y la etiqueta de la tarjeta de conteo.
- **Datos de ejemplo:** el generador añade una venta de 3 líneas con la misma tupla M1, una de ellas con "Cliente A"/"cliente a" para demostrar la normalización, y se regeneran los `.xlsx`.
- **Reglas:** actualizar `REGLAS_DESARROLLO.md` con el patrón de reporte SQL (M8, con evidencia) y el nombre de M7.

### 13.7 Ejecución y verificación
1. Implementar 13.2–13.6.
2. `-u lyd_sale_record --no-http --stop-after-init`: sin ERROR ni WARNING propios.
3. Comprobar con `psql`:
   - `\d lyd_sale_record` ya no tiene las columnas ni los `CHECK` antiguos (Odoo los elimina al actualizar: `ir_model.py:864-880`, `1881-1915`).
   - `\d lyd_sale_record_line` tiene los `CHECK`.
   - `\d+ lyd_sale_record_report` es una `VIEW`.
4. `odoo-bin shell` con rollback:
   - Importar `sales_sample.xlsx` → nº de ventas = nº de tuplas M1 distintas, y la venta de 3 líneas queda agrupada.
   - Un solo aviso de bus.
   - `amount_total` = suma de las líneas.
   - D4 en las líneas.
   - El reporte devuelve una fila por línea y sus totales cuadran con `amount_total`.
   - Los dos archivos de error se rechazan igual que antes.
5. Grep del checklist de REGLAS §9.
