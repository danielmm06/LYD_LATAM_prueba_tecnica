# Reglas de desarrollo — Módulo Odoo 19 (Prueba técnica LYD LATAM)

> **Alcance:** estas reglas aplican a todo el código del módulo. Todas se verificaron contra:
> - el código fuente local de Odoo 19 (`/Users/daniel/Documents/proyectos_odoo/odoo_19`; `odoo/release.py:15` → `version_info = (19, 0, 0, FINAL, 0, '')`),
> - la documentación oficial 19.0 (<https://www.odoo.com/documentation/19.0/reference/index.html>) y las *Coding Guidelines* 19.0 (`odoo/documentation`, rama `19.0`, `content/contributing/development/coding_guidelines.rst`),
> - los requisitos de `PRUEBA_TECNICA.md`.
>
> La columna **Evidencia** indica dónde se comprobó cada regla. Las rutas son relativas a la raíz de Odoo 19. `<module>` = **`lyd_sale_record`** (nombre aprobado, `PLAN_DESARROLLO.md` D1).

---

## 0. Protocolo de trabajo

1. **Nada se basa en suposiciones.** Antes de usar una API de Odoo (Python, XML o JS), búscala en el código fuente local (`odoo/`, `addons/`) y localiza un uso real en el core. Si no aparece, no se usa y se consulta.
2. **No se inventan reglas de negocio** (valores de estado, columnas, validaciones extra). Si hace falta una, se pregunta al usuario.
3. **Cada fase del plan se cierra** instalando o actualizando el módulo sin tracebacks ni WARNING propios en el log, con sus pruebas en verde.
4. **Nunca `cr.commit()` / `cr.rollback()`** en el código del módulo, y **nunca SQL directo** si existe un equivalente ORM. *(Coding Guidelines, "Never commit the transaction")*
5. **El código de tiempo real (bus + OWL) no se escribe** hasta que el usuario apruebe el enfoque de control de ráfagas y de limpieza de memoria (sección 8 del plan).

---

## 1. Idioma, nomenclatura y traducciones (regla obligatoria)

### 1.1 Todo identificador técnico en inglés

| Regla | Evidencia |
|---|---|
| Nombre técnico del módulo, modelos, campos, métodos, variables, XML IDs, archivos, clases JS/Python y tipos de notificación del bus: **en inglés**, `snake_case` (Python/XML) o `PascalCase`/`camelCase` (clases/JS). | Coding Guidelines, "Symbols and Conventions" |
| **Nombre del modelo = prefijo del módulo** en notación de puntos, en singular. Ej.: módulo `lyd_sale_record` → modelo `lyd.sale.record`. | Coding Guidelines: *"Model name (using the dot notation, prefix by the module name)… use singular form"* |
| **Wizard (TransientModel):** `<modelo_base>.<acción>`, **sin la palabra "wizard"**. Ej.: `lyd.sale.record.import`. | Coding Guidelines: *"use `<related_base_model>.<action>`… Avoid the wizard word"* |
| **Reporte sobre vista SQL:** `<modelo_base>.report`. Ej.: `lyd.sale.record.report` (M7). | Patrón de nomenclatura del proyecto; `addons/sale/report/sale_report.py:10` (`sale.report`), `addons/account/report/account_invoice_report.py:12` (`account.invoice.report`) |
| Clases Python en PascalCase derivadas del `_name` (ej.: `LydSaleRecord`, `LydSaleRecordImport`). | Coding Guidelines, "Odoo Python Class" |
| Sufijo `_id` solo para `Many2one` y `_ids` solo para `One2many`/`Many2many`. Los campos relacionales siguen los nombres del core de ventas: `partner_id` (cliente), `user_id` (vendedor), `product_id` (producto). | Coding Guidelines, "Variable name" / "Many2One fields"; `addons/sale/models/sale_order.py:65, 208`; `addons/sale/models/sale_order_line.py:83` |
| Métodos: `_compute_<campo>`, `_search_<campo>`, `_default_<campo>`, `_selection_<campo>`, `_onchange_<campo>`, `_check_<restricción>`, `action_<verbo>` (con `self.ensure_one()` si opera sobre un registro). | Coding Guidelines, "Method conventions" |
| Orden dentro del modelo: atributos privados → métodos default → campos → restricciones SQL/índices → compute/inverse/search → selection → `@api.constrains`/`@api.onchange` → CRUD → acciones → negocio. | Coding Guidelines, "In a Model attribute order should be" |
| Tipo de notificación del bus con el prefijo del modelo: `<model_name>/<event>` (ej.: `lyd.sale.record/created`). | Convención del core: `im_livechat.looking_for_help/update` en `addons/im_livechat/models/discuss_channel.py:212-214` |

### 1.2 Archivos y XML IDs

| Elemento | Patrón | Evidencia |
|---|---|---|
| Modelo principal | `models/<model_name>.py` (si hay un solo modelo, igual que el módulo) | Coding Guidelines, "File naming" |
| Wizard | `wizard/<transient>.py` + `wizard/<transient>_views.xml` | idem |
| Vistas | `views/<model_name>_views.xml`; menús principales en `views/<module>_menus.xml` | idem |
| Seguridad | `security/ir.model.access.csv`, `security/<module>_groups.xml`, `security/<model>_security.xml` (reglas) | idem |
| Vista | `<model_name>_view_<view_type>`; `name` = el mismo con puntos (`lyd.sale.record.view.list`) | Coding Guidelines, "XML IDs and naming" |
| Acción | `<model_name>_action` (principal), `<model_name>_action_<detalle>` (resto) | idem |
| Menú | `<model_name>_menu` / `<model_name>_menu_<detalle>`; raíz `<module>_menu_root` | idem |
| Grupo | `<module>_group_<nombre>` (`user`, `manager`) | idem |
| Regla de registro | `<model_name>_rule_<grupo>` | idem |
| JS / QWeb / SCSS | Un componente por archivo, con nombre descriptivo, bajo `static/src/…` | Coding Guidelines, "Static files organization" |

### 1.3 Textos visibles: en inglés en el código y traducidos al español

| Regla | Evidencia |
|---|---|
| **Todo texto visible se escribe en inglés** en el código fuente (`string=`, `help=`, etiquetas de `Selection`, `_description`, nombres de acciones y menús, textos de vistas, mensajes de error, `models.Constraint`, textos JS). **El español se entrega mediante `i18n/es.po`.** | Coding Guidelines, "Use translation method correctly" |
| Python: `self.env._("literal")` con parámetros **dentro** de la llamada (`self.env._("Row %(row)s: …", row=n)`). Nunca formatear antes ni fuera (`_("…" % x)` o `_("…") % x`). Nada de concatenaciones ni cadenas dinámicas. | Coding Guidelines, idem; `odoo/orm/environments.py:315` (`def _`) |
| JS: `import { _t } from "@web/core/l10n/translation";` → `_t("literal")`. | `addons/web/static/src/core/l10n/translation.js`; `addons/web/static/src/views/list/list_controller.js:1` |
| Extracción de términos: en Python, las palabras clave `_` y `_lt` (incluye `self.env._`); en JS, `_t` dentro de `static/src`; y los templates QWeb. | `odoo/tools/translate.py:1488-1500` |
| Los mensajes de `models.Constraint` se guardan en `ir.model.constraint.message` y se exportan como `model:ir.model.constraint,message:…`, así que **también se traducen en el `.po`**. | `odoo/orm/models.py:3276-3291`; `addons/sale/i18n/sale.pot` (entrada `constraint_res_company_check_quotation_validity_days`) |
| **Archivo de traducción: `i18n/es.po`.** Para cualquier idioma `es_XX` Odoo carga, en este orden, `es.po` → `es_419.po` → `es_XX.po`. Un solo `es.po` cubre `es_CO`, `es_419`, `es_ES`, etc. | `odoo/tools/translate.py:1823-1845` (`get_base_langs`, `get_po_paths`) |
| **Plantilla `.pot`:** `./odoo-bin i18n export -c <cfg> -d <db> <module>`. Escribe `<module>/i18n/<module>.pot`. Con `-l <iso_code>` exporta `<iso_code>.po` (el idioma tiene que estar activo). | `odoo/cli/i18n.py` (`_export`, `i18n_path / f'{module_name}.pot'`) |
| No traducir **valores de datos** (nombres de clientes, productos, etc.). `_()` es solo para literales estáticos. | Coding Guidelines, "Use translation method correctly" |
| **Excepción justificada:** las **cabeceras del Excel** (`Fecha`, `Cliente`, `Vendedor`, `Producto`, `Cantidad`, `Valor Unitario`, `Valor Total`, `Estado`) son el **contrato del archivo** definido en el PDF, no textos de interfaz. Van como constantes en el código, en una sola tabla de correspondencia cabecera → campo. Lo mismo vale para el **diccionario de valores de "Estado"** del Excel (`borrador`/`confirmada`/`cancelada` → `draft`/`confirmed`/`cancelled`): es una tabla de entrada de datos, no un texto de interfaz. Las etiquetas visibles de la `Selection` siguen en inglés y se traducen en `es.po`. | `PRUEBA_TECNICA.md`, "Estructura del archivo Excel"; decisión D3 |

---

## 2. Entorno

| Regla | Evidencia |
|---|---|
| Python del venv: **3.12.11**. | `venv/bin/python --version` |
| **`.xlsx` se lee con `openpyxl` 3.1.2** (dependencia oficial). `xlrd` 2.0.1 **no lee `.xlsx`**. | `requirements.txt:48-49, 99-100`; `addons/base_import/models/base_import.py:473-484` |
| Lectura: `openpyxl.load_workbook(io.BytesIO(data), data_only=True)`. Las fechas llegan como `datetime`; los números como `int`/`float`; las celdas vacías como `None`. Detectar `cell.data_type == TYPE_ERROR` (celdas `#VALUE!`, etc.). | `addons/base_import/models/base_import.py:484-515` |
| Excepciones concretas de un archivo inválido: `zipfile.BadZipFile`, `openpyxl.utils.exceptions.InvalidFileException`, `KeyError`, `ValueError`. **No usar `except Exception`.** | Comprobado en el venv; Coding Guidelines, "Avoid catching exceptions" |
| Servidor en `workers = 0` (modo *threaded*): el bus funciona sin *gevent* aparte. | `addons/bus/models/bus.py` (`ImDispatch`); `configs/demos.cfg` (`workers = 0`) |

---

## 3. Manifest

| Regla | Evidencia |
|---|---|
| `'version': '19.0.1.0.0'`, `'license': 'LGPL-3'` explícita. | `odoo/modules/module.py:433, 550-564` (`adapt_version`); `addons/bus/__manifest__.py:38` |
| `'depends': ['base', 'web', 'bus', 'product']`. `bus` es `auto_install`, pero lo usamos directamente, así que la dependencia va explícita. `product` es necesario para `product.product` (D2) y arrastra `mail` y `uom`. **No** añadir `sale`, `board` ni `spreadsheet_dashboard`. | `addons/bus/__manifest__.py:6, 11`; `addons/product/__manifest__.py:7` |
| `'external_dependencies': {'python': ['openpyxl']}`. | `odoo/modules/module.py:76, 254`; `addons/auth_ldap/__manifest__.py:13` |
| Assets: `'assets': {'web.assets_backend': ['<module>/static/src/**/*']}`. Tests JS (si se hacen): `'web.assets_unit_tests': ['<module>/static/tests/**/*']`. | `addons/bus/__manifest__.py:12-19`; `addons/calendar/__manifest__.py:49-51` |
| Orden de `data`: grupos → `ir.model.access.csv` → reglas → vistas → vistas del wizard → menús (los menús referencian acciones). | Dependencias de XML IDs |

---

## 4. ORM (Python)

| Regla | Evidencia |
|---|---|
| **`_sql_constraints` está PROHIBIDO**: en v19 solo emite un WARNING y la restricción **no se crea**. Usar `models.Constraint('CHECK (…)', "English message")` en un atributo que empiece por `_`. | `odoo/orm/model_classes.py:161-163`; `odoo/orm/table_objects.py:42-44, 79-104`; `addons/sale/models/res_company.py:11-14` |
| `_constraints` también está prohibido (WARNING). Usar `@api.constrains`. | `odoo/orm/model_classes.py:158-160` |
| Todo modelo lleva `_description` (si falta, WARNING). | `odoo/orm/model_classes.py:275` |
| Obligatorios: `required=True` (crea `NOT NULL`). | ORM estándar |
| Agregación: `aggregator=` (nunca `group_operator`, obsoleto desde la 18). `Integer`/`Float`/`Monetary` ya suman por defecto. | `odoo/orm/fields.py:485-487`; `odoo/orm/fields_numeric.py:23, 112, 201` |
| `create` en lote: `@api.model_create_multi def create(self, vals_list)`. **Un solo `create(vals_list)` por importación.** | `odoo/orm/decorators.py`; Coding Guidelines, "Programming in Odoo" |
| Agrupaciones del lado servidor: `_read_group(domain, groupby, aggregates)`. **`read_group` está obsoleto.** Para el cliente: `formatted_read_group` / `web_read_group`. | `odoo/orm/models.py:1867, 2755-2756`; `addons/web/models/models.py:349, 802` |
| Métodos de solo lectura llamados por RPC: `@api.readonly`. | `odoo/orm/decorators.py:345` |
| Métodos llamables por RPC (botones, `orm.call`): **públicos** (sin `_`). Los helpers internos, privados (`_`). | `odoo/service/model.py:45` (`get_public_method`) |
| Nunca `self._cr`, `self._uid`, `self._context`: usar `self.env.cr`, `self.env.uid`, `self.env.context`. | Coding Guidelines, "Propagate the context" |
| **Precio unitario como en `sale.order.line`:** `fields.Float(min_display_digits='Product Price')`. Con `min_display_digits` y sin `digits`, la columna es `NUMERIC` sin precisión fija: guarda todos los dígitos significativos y muestra al menos los decimales de *Product Price*. Así `price_total / quantity` se guarda sin truncar. | `odoo/orm/fields_numeric.py:69-76, 121-133`; `addons/sale/models/sale_order_line.py:177-181`; `addons/product/data/product_data.xml:19-21` |
| **Cantidad como en `sale.order.line`:** `fields.Float(digits='Product Unit')`. | `addons/sale/models/sale_order_line.py:127-131`; `addons/uom/data/uom_data.xml:6` |
| Comparar importes con la moneda: `currency.compare_amounts(a, b)`, `currency.is_zero(x)`, `currency.round(x)`. Nunca `==` entre floats. | `odoo/addons/base/models/res_currency.py:216, 225, 248` |
| Errores para el usuario: `UserError` (flujo) y `ValidationError` (datos), de `odoo.exceptions`, con texto traducible. | Uso generalizado en `addons/*/models` |
| `try/except` solo con excepciones concretas y en el bloque mínimo necesario. Si hay que capturar excepciones del framework, dentro de `with self.env.cr.savepoint():`. | Coding Guidelines, "Avoid catching exceptions" |

---

## 4 bis. Relacionar y crear registros relacionados (cliente, vendedor, producto)

| Regla | Evidencia |
|---|---|
| **Modelos del core:** cliente → `res.partner` (como `sale.order.partner_id`), vendedor → `res.users` interno (`share = False`, como `sale.order.user_id`), producto → `product.product` (como `sale.order.line.product_id`). | `addons/sale/models/sale_order.py:65-70, 208-216`; `addons/sale/models/sale_order_line.py:83-88` |
| **Búsqueda por nombre como el core:** `('name', '=ilike', nombre_normalizado)`, sin distinguir mayúsculas, con `limit=1` y el dominio de compañía `_check_company_domain(company)`. El nombre se normaliza con `strip()` y colapsando espacios. | `addons/account/models/partner.py:1008-1026`; `addons/account/models/product.py:540-555`; `odoo/orm/models.py:4003` |
| **Nombres en la búsqueda:** escapar `_` y `%` con `escape_psql` antes de usar `=ilike` (si no, funcionan como comodines de SQL y "Cliente_A" coincidiría con "Cliente A"). La caché por importación usa como clave `strip().lower()` de Python. Limitación conocida: Odoo crea las BD con `LC_COLLATE 'C'`, y así `ILIKE` no pliega mayúsculas acentuadas (`'ÑANDÚ' ILIKE 'ñandú'` es falso). Entre importaciones distintas, "ÑANDÚ PÉREZ" no encuentra a "Ñandú Pérez"; es la misma limitación del core. | `odoo/tools/sql.py:673` (`escape_psql`); `odoo/service/db.py:142-146`; tests `test_wildcard_characters_do_not_match_other_records` y `test_new_records_are_created_once` |
| **Si no existe, se crea** con los valores mínimos (`name`; en usuarios, también `login`). Se crea **una sola vez por nombre y por importación** (caché `{nombre_normalizado: registro}`), igual que la caché de `_import_retrieve_customer`. | `addons/account/models/partner.py:1021-1066`; decisión D2 |
| **Permisos:** un usuario interno normal **no puede** crear contactos (`base.group_partner_manager`), productos (`product.group_product_manager`) ni usuarios (`base.group_erp_manager`). La estrategia aprobada está en el plan (decisión N1); no se añaden `sudo()` fuera de ella. | `odoo/addons/base/security/ir.model.access.csv:75-76, 85-86`; `addons/product/security/ir.model.access.csv:3, 8, 19, 23` |
| **Usuarios nuevos:** `login` obligatorio y único (`_login_key`). Sin contraseña no pueden iniciar sesión. Reciben `base.group_user` + los grupos implicados por `base.default_user_group`. Al crearlos, `mail` solo registra una nota si el usuario es de portal; no envía correos. | `odoo/addons/base/models/res_users.py:203-216, 274`; `addons/mail/models/res_users.py:180-200` |
| Producto nuevo: `product.product.create({'name': …})` crea también su `product.template`, con el tipo por defecto `consu` ("Goods"). | `addons/product/models/product_template.py:54-64` |
| Many2one obligatorios con `ondelete='restrict'`: no se puede borrar un cliente, vendedor o producto que tenga ventas. | `addons/sale/models/sale_order_line.py:86` (`ondelete='restrict'`) |

---

## 4 ter. Reportes sobre vista SQL (M7/M8)

| Regla | Evidencia |
|---|---|
| Un reporte de análisis (agregación entre modelos, p. ej. líneas × cabecera) se modela como `_auto = False` sobre una **vista PostgreSQL real**, creada en `init()` con `drop_view_if_exists(self.env.cr, self._table)` seguido de `self.env.cr.execute(SQL("CREATE OR REPLACE VIEW %s AS (%s)", SQL.identifier(self._table), <query>))`. | `addons/fleet/report/fleet_report.py:150-151`; `odoo/tools/sql.py:665` (`drop_view_if_exists`) |
| **Excepción justificada a la regla "nunca SQL directo" (§0.4):** el ORM no tiene equivalente para definir una vista de reporte que una varias tablas con `JOIN`. Se permite **solo** dentro de `init()`, y **solo** con objetos `SQL` / `SQL.identifier` (nunca `%` ni f-strings con valores dentro de la cadena SQL). | `odoo/tools/sql.py` (clase `SQL`); mismo patrón en `addons/account/report/account_invoice_report.py:60-79` (`_table_query`) y `addons/sale/report/sale_report.py:9-14` |
| Todos los campos del reporte son `readonly=True` (son de solo lectura, vienen de la vista). | `addons/sale/report/sale_report.py:21-80` |
| `_depends = {'<modelo>': [...], ...}` invalida la caché del reporte cuando cambian los modelos de origen, igual que un campo `related`. | `addons/account/report/account_invoice_report.py:60-79` |
| Naming: `<modelo_base>.report` (sección 1.1). Acceso: solo lectura para todos los grupos (`perm_write/create/unlink = 0`), igual que `sale.report`. | `addons/sale/security/ir.model.access.csv:41` (`access_sale_report_salesman`) |

## 5. Seguridad

| Regla | Evidencia |
|---|---|
| `security/ir.model.access.csv` con la cabecera `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`. | `addons/sale/security/ir.model.access.csv:1` |
| **El TransientModel (wizard) también necesita ACL.** `ir.model.access.check` solo exime al superusuario. Si falta, aparece un WARNING al cargar y un AccessError al usarlo. | `odoo/addons/base/models/ir_model.py:2163-2176`; `odoo/modules/loading.py:257` |
| Grupos v19: `res.groups.privilege` (`privilege_id`) + `res.groups` con `implied_ids`. | `addons/sales_team/security/sales_team_security.xml:3-30`; `odoo/addons/base/models/res_groups_privilege.py:4-5` |
| Payload del bus **mínimo y no sensible**. El cliente vuelve a leer por ORM, que aplica ACL y reglas. | Criterio de diseño (sección 7) |

---

## 6. Vistas XML y acciones

| Regla | Evidencia |
|---|---|
| **La raíz de la vista de lista es `<list>`**; `view_mode` usa `list` (nunca `tree`). | `odoo/addons/base/rng/list_view.rng:24` |
| Visibilidad y solo lectura condicionales con `invisible="expr"` / `readonly="expr"` / `required="expr"`. **`attrs` y `states` no existen.** | `odoo/addons/base/models/ir_ui_view.py:495` (*"Since 17.0, the attrs and states attributes are no longer used"*) |
| Graph: `type` ∈ `bar` \| `pie` \| `line`; atributos: `stacked`, `order`, `sample`, `disable_linking`, `cumulated`, `js_class`. | `odoo/addons/base/rng/graph_view.rng:11-28` |
| Pivot: `<field name="date" interval="month" type="row"/>`, `type="col"`, `type="measure"`. | `odoo/addons/base/rng/pivot_view.rng`; `addons/sale/report/sale_report_views.xml:8-12` |
| Filtro de fecha: `<filter name="filter_date" date="date"/>` (opcional `default_period`). Agrupaciones: `context="{'group_by': 'field'}"`. | `addons/sale/report/sale_report_views.xml:82-86` |
| Totales en el pie de la lista (`sum="…"`): **se calculan en el cliente sobre los registros cargados** (la página o la selección), no sobre todo el dominio. No sirven para el KPI "Total vendido en el mes". | `addons/web/static/src/views/list/list_renderer.js:697-784` |
| Vista con comportamiento propio: atributo `js_class="<nombre_registrado>"` en la raíz. | `addons/calendar/views/calendar_views.xml:76` |
| Campo de archivo en el wizard: `fields.Binary(required=True, attachment=False)` + `Char` para el nombre; en la vista, `<field name="file" filename="file_name" options="{'accepted_file_extensions': '.xlsx'}"/>` y `<field name="file_name" invisible="1"/>`. | `odoo/addons/base/wizard/base_import_language.py:23-24`; `odoo/addons/base/wizard/base_import_language_views.xml:13-14` |
| Aviso al terminar: devolver `{'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title', 'message', 'type', 'sticky', 'next'}}`; `next` es la acción que se ejecuta después. | `addons/web/static/src/webclient/actions/client_actions.js:5-26` |
| Tablero y menús mediante `ir.actions.act_window`. | Requisito del proyecto |

---

## 7. Tiempo real (bus + OWL)

### 7.1 Servidor

| Regla | Evidencia |
|---|---|
| **Enviar con `record._bus_send(type, payload)`** (`bus.listener.mixin`). El docstring de `_sendone` lo recomienda: *"Using `_bus_send()` … is recommended for simplicity and security"*. | `addons/bus/models/bus.py:111-118`; `addons/bus/models/bus_listener_mixin.py` |
| **Canal = registro `res.groups`.** `res.groups` ya hereda de `bus.listener.mixin`, y cada websocket se suscribe automáticamente a los `all_group_ids` del usuario (incluye los grupos implicados). Así no hace falta `addChannel` y solo lo reciben los usuarios del grupo. | `addons/bus/models/res_groups.py:8`; `addons/bus/models/ir_websocket.py:15-28`; `odoo/addons/base/models/res_users.py:258`; ejemplo del core: `addons/im_livechat/models/discuss_channel.py:212` |
| **Prohibido un canal string "adivinable"**: el cliente puede suscribirse a cualquier string (solo se valida que sea `str`). | `addons/bus/models/ir_websocket.py:57-58`; `addons/bus/models/bus.py:116-118` |
| **Semántica transaccional:** la notificación se inserta en *precommit* y se emite con `NOTIFY` en *postcommit*. El navegador solo se entera cuando los datos ya están confirmados; si hay rollback (p. ej. `UserError` en el wizard), no se envía nada. | `addons/bus/models/bus.py:121-160` |
| **Emitir desde `create()` del modelo** (no desde el wizard), **una vez por llamada a `create`** (por lote), después de `super().create()`. Así avisa tanto la importación como la creación manual o una integración externa. | Requisito del PDF |

### 7.2 Cliente (OWL, Odoo 19)

| Regla | Evidencia |
|---|---|
| Servicio: `useService("bus_service")`. API: `subscribe(type, callback)` / `unsubscribe(type, callback)` con **la misma referencia** de callback (internamente usa un `Map` callback → wrapper). **No usar** `addEventListener("notification", …)`. | `addons/bus/static/src/services/bus_service.js:50-51, 208-235` |
| El bus ya está arrancado en el backend: no llamar a `bus_service.start()`. | `addons/bus/static/src/simple_notification_service.js:5-11` |
| **Prohibido el polling** (`setInterval` / `setTimeout` recurrente que consulte al servidor). Un temporizador solo puede **agrupar eventos ya recibidos** (throttle). | Requisito del PDF ("no se puede depender de un polling agresivo") |
| **Integración con la lista nativa:** extender `ListController` sin duplicar el renderizado (se reutiliza el template `web.ListView`, el renderer y el `RelationalModel`). Mecanismo según la decisión D6 del plan: `js_class` + subclase registrada con `registry.category("views").add(name, {...listView, Controller})`, o `patch` de `ListController`. | `addons/web/static/src/views/list/list_controller.js:39-40`; `addons/web/static/src/views/list/list_view.js`; `addons/calendar/static/src/views/list_view/calendar_list_view.js` |
| Recarga: `this.model.load()`. Conserva dominio, orden, agrupación y paginación, y usa `KeepLast`: si hay cargas solapadas, solo se aplica la última. | `addons/web/static/src/views/list/list_controller.js:117`; `addons/web/static/src/model/relational_model/relational_model.js:193-214` |
| Recargar crea un `root` nuevo: **se pierde la selección y la edición en línea**. Si `this.model.root.editedRecord` existe o `this.model.root.selection.length > 0`, se aplaza la recarga. | `addons/web/static/src/model/relational_model/relational_model.js:211`; `…/dynamic_list.js:55, 75` |
| **No existe throttle temporal en el core** ni Lodash. `@web/core/utils/timing` exporta `batched`, `debounce`, `setRecurringAnimationFrame`, `throttleForAnimation`, `useDebounced`, `useThrottleForAnimation`. **El `debounce` del core reinicia el temporizador en cada llamada**, así que no sirve para flujos sostenidos. → Throttle propio *leading + trailing* con `browser.setTimeout` / `browser.clearTimeout`. | `addons/web/static/src/core/utils/timing.js:11-207` (`debounce` 45-91); `addons/web/static/src/core/browser/browser.js:35-36` |
| **Limpieza obligatoria en `onWillUnmount`:** `unsubscribe` + `clearTimeout` del temporizador pendiente + descartar lo pendiente. En el callback asíncrono, comprobar `status(this) === "destroyed"` (de `@odoo/owl`) antes de tocar el modelo. | `addons/web/static/src/core/utils/timing.js:188-200` (patrón cancel-on-unmount); `addons/web/static/src/views/list/list_renderer.js:292` |
| Componentes auxiliares dentro de la lista (p. ej. KPIs): heredar el template con `t-inherit="web.ListRenderer" t-inherit-mode="primary"` y un `xpath` sobre `div.o_list_renderer`, y refrescar en `onWillUpdateProps` (se dispara cuando la lista se recarga). | `addons/purchase/static/src/views/purchase_listview.js` y `.xml`; `addons/purchase/static/src/views/purchase_dashboard.js:8-17`; `addons/web/static/src/views/list/list_renderer.xml:4-7` |
| Imports OWL desde `@odoo/owl`; servicios con `useService` (`@web/core/utils/hooks`); `registry` desde `@web/core/registry`. Módulos ES sin `/** @odoo-module */` (el core de v19 ya no lo usa). | `addons/web/static/src/views/list/list_controller.js:1-24`; `addons/purchase/static/src/views/purchase_listview.js` |

---

## 8. Pruebas

| Regla | Evidencia |
|---|---|
| Tests Python en `tests/` con `TransactionCase` (importado desde `odoo.tests`) y etiquetas `@tagged('post_install', '-at_install')` cuando dependan de vistas o assets. | `addons/bus/tests/test_notify.py:8-13` |
| Comprobar las notificaciones del bus: tras `create`, ejecutar `self.env.cr.precommit.run()` y buscar en `bus.bus` por `channel` / `message`. | `odoo/tools/misc.py:1170` (`Callbacks.run`); `addons/account/tests/test_account_account.py:696` |
| Ejecución: `./odoo-bin -c <cfg> -d <db> -u <module> --test-enable --test-tags /<module> --stop-after-init`. | `odoo/tools/config.py:285-307, 433` |

---

## 9. Checklist para cerrar cada fase

- [ ] El módulo instala o actualiza (`-u <module>`) sin tracebacks y sin WARNING propios (en especial `_sql_constraints`, `_description` y ACL faltante).
- [ ] Ninguna aparición de: `<tree`, `attrs=`, `states=`, `group_operator`, `_sql_constraints`, `read_group(`, `self._cr`, `self._context`, `cr.commit()`, `except Exception`, `setInterval`, `addEventListener("notification"`, `owl.utils`, `lodash`.
- [ ] Identificadores técnicos en inglés; ningún texto de interfaz escrito directamente en español en el código (salvo las cabeceras del Excel, sección 1.3).
- [ ] `i18n/<module>.pot` regenerado y `i18n/es.po` sin entradas vacías (`msgstr ""`).
- [ ] Tests de la fase en verde.
- [ ] Cada API nueva usada tiene su evidencia (archivo:línea).
