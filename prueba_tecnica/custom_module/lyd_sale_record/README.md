# Sale Record Import & Dashboard (`lyd_sale_record`)

Módulo para **Odoo 19** que importa desde un Excel las ventas del mes, las guarda con una estructura **cabecera + líneas** (como `sale.order` / `sale.order.line`), las analiza en un **tablero comercial** y muestra en **tiempo real**, sin recargar la página, las ventas nuevas que crean otros usuarios o procesos.

- Versión: `19.0.1.1.0` · Licencia: LGPL-3
- Dependencias: `base`, `web`, `bus`, `product` (que a su vez instala `mail` y `uom`) · Python: `openpyxl`

---

## 1. Instalación

En los comandos, sustituye los marcadores por los valores de tu entorno:

| Marcador | Significado |
|---|---|
| `/ruta/a/odoo` | Carpeta del código fuente de Odoo 19 (la que contiene `odoo-bin`). |
| `/ruta/a/custom_module` | Carpeta `custom_module/` de este repositorio, la que **contiene** la carpeta `lyd_sale_record/` (no la del módulo en sí). |
| `/ruta/a/odoo.conf` | Tu archivo de configuración de Odoo (opcional). |
| `<mi_base>` | Nombre de la base de datos donde se instala el módulo. |

1. **Requisitos:** Odoo 19 (Community o Enterprise) funcionando, Python ≥ 3.12 y PostgreSQL.
2. **Dependencia Python:** `openpyxl` ya forma parte de los requisitos oficiales de Odoo 19 (`requirements.txt`, `openpyxl==3.1.2`). Si falta, instálalo con el mismo intérprete (o entorno virtual) con el que ejecutas Odoo:
   ```bash
   python3 -m pip install openpyxl
   ```
3. **Obtener el módulo:** clona o copia este repositorio en cualquier ubicación. Lo que Odoo necesita es la carpeta `custom_module/`, que contiene `lyd_sale_record/`.
4. **addons_path:** añade `/ruta/a/custom_module` a la ruta de addons, junto a los addons estándar de Odoo. Hay dos formas:
   - **En el archivo de configuración** (`odoo.conf`):
     ```ini
     [options]
     addons_path = /ruta/a/odoo/addons,/ruta/a/custom_module
     db_host = localhost
     db_port = 5432
     db_user = odoo
     db_password = odoo
     ```
   - **Por línea de comandos:** `--addons-path=/ruta/a/odoo/addons,/ruta/a/custom_module`.
5. **Instalar:** desde la carpeta de Odoo (`cd /ruta/a/odoo`):
   ```bash
   # Con archivo de configuración
   ./odoo-bin -c /ruta/a/odoo.conf -d <mi_base> -i lyd_sale_record --stop-after-init

   # Sin archivo de configuración
   ./odoo-bin --addons-path=/ruta/a/odoo/addons,/ruta/a/custom_module -d <mi_base> -i lyd_sale_record --stop-after-init
   ```
   Si la base `<mi_base>` no existe, Odoo la crea. Después arranca el servidor normalmente (los mismos comandos sin `-i` ni `--stop-after-init`).

   **Desde la interfaz:** con el servidor arrancado con el `addons_path` anterior, activa el modo desarrollador, ve a *Aplicaciones → Actualizar lista de aplicaciones*, quita el filtro *Aplicaciones* de la búsqueda, busca *Sale Record Import & Dashboard* y pulsa *Activar*.
6. **Actualizar** (tras cambiar el código del módulo): igual que instalar, pero con `-u lyd_sale_record` en lugar de `-i lyd_sale_record`.
7. **Idioma:** el código está en inglés y la traducción al español está en `i18n/es.po`. Odoo lo carga para cualquier variante de español (`es_CO`, `es_419`, `es_ES`…), porque primero busca `es.po`. Activa el idioma en *Ajustes → Idiomas* y asígnalo al usuario.
8. **Permisos:** asigna a cada usuario el privilegio *Registro de venta* en *Ajustes → Usuarios*:
   - **Usuario:** ve, crea e importa ventas; puede quitar líneas de una venta.
   - **Gerente:** además puede borrar ventas. El administrador lo recibe al instalar el módulo.

   Solo los usuarios de estos grupos reciben las notificaciones en tiempo real.

## 2. Uso

Menú **Registros de venta**:

| Menú | Qué hace |
|---|---|
| **Tablero** | Análisis de ventas (graph de barras/circular/líneas y pivot) sobre el reporte SQL, una fila por línea de venta. Se abre filtrado por el mes actual (filtro de fecha por defecto); quita el filtro para ver todo. |
| **Registros de venta** | Lista de ventas con **tarjetas KPI** (total y número de ventas del mes actual y del filtro activo) y **actualización en tiempo real**. El formulario muestra la cabecera y sus líneas editables. |
| **Importar Excel** | Asistente de importación. |

### 2.1 Formato del Excel

Primera hoja, primera fila con estas 8 cabeceras (en cualquier orden; no importan mayúsculas ni espacios):

| Fecha | Cliente | Vendedor | Producto | Cantidad | Valor Unitario | Valor Total | Estado |
|---|---|---|---|---|---|---|---|
| 2026-06-01 | Cliente A | Juan Pérez | Producto 1 | 2 | 50000 | 100000 | Confirmada |

- **Fecha:** celda de fecha de Excel o texto `AAAA-MM-DD`.
- **Estado:** `Borrador`, `Confirmada` o `Cancelada`, o sus claves técnicas `draft`, `confirmed` o `cancelled`. Se normaliza con `strip().lower()`, así que `CONFIRMADA` y ` confirmada ` también valen.
- **Formato:** solo se admite `.xlsx`. Cualquier otro formato muestra *"Formato no soportado. Por favor, cargue un archivo con extensión .xlsx"*.

En `../../sample_data/` hay archivos de ejemplo, su generador y una **guía de pruebas manuales** (`sample_data/README.md`).

### 2.2 Reglas de la importación

- **Validaciones por fila:** la fecha tiene que ser válida; cliente, vendedor, producto y estado son obligatorios; cantidad y valor total tienen que ser números mayores que cero; el valor unitario, si viene, tiene que ser numérico. Además se rechazan las celdas con error de Excel (`#DIV/0!`…).
- **Todo o nada:** si alguna fila es inválida no se crea nada y se muestran todos los errores (fila, columna y motivo; los 50 primeros).
- **Agrupación en ventas:** las filas con la misma **(Fecha, Cliente, Vendedor, Estado)** forman **una venta** y cada fila es una línea. Cliente y vendedor se comparan normalizados.
- **Clientes, vendedores y productos:** se buscan por nombre exacto sin distinguir mayúsculas (`=ilike`, como el importador de facturas del core) y, si no existen, se **crean**. Un usuario normal no tiene permiso para crearlos, así que el asistente los crea con `sudo()` escribiendo solo el nombre (y el login en los usuarios). Si hay homónimos, se usa el primero según el orden del modelo (en los vendedores, primero los activos).
- **Rendimiento (caché precargada):** antes de crear las ventas se reúnen los nombres **únicos** de clientes, vendedores y productos del archivo, normalizados (sin espacios en los extremos y en minúsculas). Cada modelo se consulta **una sola vez**, con un `OR` de todos los nombres, en lotes de 500 como máximo (`SEARCH_BATCH_SIZE`). Los que faltan se crean con un solo `create()` por modelo. El número de consultas no depende del número de filas: un archivo con 1.000 clientes, 50 vendedores y 300 productos distintos pasa de unas 1.350 búsquedas a 3, más 3 creaciones y 1 consulta de logins. Los registros nuevos conservan la forma en que se escribió el nombre la primera vez en el archivo.
- **Vendedores nuevos:** se crean como usuarios internos **sin contraseña**, con un login generado a partir del nombre (`juan.perez`, y `juan.perez.2`… si está ocupado, también por un usuario archivado). Los logins ocupados se leen en una sola consulta, y dos vendedores nuevos del mismo archivo que generen el mismo login reciben `juan.perez` y `juan.perez.2`. Antes de crear uno siempre se busca, **incluidos los archivados**. ⚠️ En Odoo Enterprise cada usuario interno ocupa una licencia.
- **Precio unitario:** si `Valor Total ≠ Cantidad × Valor Unitario`, o si falta el valor unitario, se ajusta a `Valor Total / Cantidad` y la línea queda marcada como **Precio unitario ajustado** (se puede filtrar). La regla está en el modelo, así que también se aplica al crear o editar a mano o por API.

## 3. Arquitectura

| Pieza | Descripción |
|---|---|
| `lyd.sale.record` | Cabecera: fecha, cliente (`res.partner`), vendedor (`res.users`), estado, compañía, moneda, archivo de origen, `line_ids` y `amount_total` (calculado y guardado). |
| `lyd.sale.record.line` | Línea: producto (`product.product`), cantidad, precio unitario, total y marca de ajuste. Restricciones SQL `quantity > 0` y `price_total > 0` (`models.Constraint`). |
| `lyd.sale.record.report` | Reporte sobre una **vista PostgreSQL real** (`_auto = False` + `CREATE OR REPLACE VIEW` en `init()`, con objetos `SQL`). Da una fila por línea con los datos de su cabecera. No duplica información y alimenta el graph y el pivot. Los estados salen de la constante `SALE_RECORD_STATE`, compartida con la cabecera (como `SALE_ORDER_STATE` en `sale.report`). |
| `lyd.sale.record.import` | Asistente (TransientModel) que lee el `.xlsx` con `openpyxl`, valida, agrupa, precarga clientes, vendedores y productos (una búsqueda por modelo, con `_get_or_create_records()`) y crea todas las ventas en **un solo** `create()`. |
| `realtime_list/` (JS) | `RealtimeListController` (subclase de `ListController`) + renderer con las tarjetas KPI, registrados como vista `lyd_sale_record_realtime_list` y activados con `js_class` en la lista de ventas. |

Seguridad: ACL para los 4 modelos (el reporte, solo lectura) y reglas multicompañía para la cabecera, la línea y el reporte.

## 4. Notificaciones en tiempo real (respuestas del requisito)

### 4.1 Mecanismo de notificación

Se usa el **bus de Odoo (`bus.bus`) sobre WebSocket**, sin polling.

- **Qué dispara el aviso:** el `create()` de `lyd.sale.record`. Tras crear el lote llama a `grupo._bus_send('lyd.sale.record/created', {'count': n})` sobre el grupo *Usuario* del módulo (`res.groups` hereda de `bus.listener.mixin`). Lanzarlo desde el modelo, y no desde el asistente, cubre la importación, la creación manual y las integraciones externas (API).
- **Garantía transaccional:** el bus guarda el mensaje en *precommit* y lo emite con `NOTIFY` en *postcommit*. El navegador solo se entera cuando los datos ya están confirmados. Si la importación falla y se deshace la transacción, no se envía nada.
- **Por qué este canal:** cada WebSocket ya está suscrito a los grupos de su usuario, así que no hace falta `addChannel` y solo reciben el aviso los usuarios con acceso. Los canales de texto "adivinables" se evitan, porque cualquier cliente puede suscribirse a ellos.
- **Qué lo recibe:** en el navegador, el `bus_service` (un SharedWorker con una sola conexión compartida entre pestañas) entrega el aviso al controlador de la lista, que se suscribió con `bus_service.subscribe("lyd.sale.record/created", callback)`. El payload no lleva datos: la lista vuelve a leer por ORM, respetando permisos y reglas.
- **Un aviso por lote:** una importación de N ventas produce un único aviso. Editar una venta o añadirle líneas no avisa, porque no es un registro nuevo.

### 4.2 Control de ráfagas: throttle con flanco inicial y final

Se aplica **una recarga como máximo cada 2 s** (`RELOAD_THROTTLE_INTERVAL`), y el último evento nunca se pierde:

- **Flanco inicial:** si hace más de 2 s que no se recarga, el primer aviso recarga **de inmediato**.
- **Mientras la ventana de 2 s está abierta:** los avisos no programan más recargas; solo marcan que hay algo pendiente.
- **Flanco final:** al cerrarse la ventana, si hay algo pendiente, se recarga una vez más.

Resultado:
- **Ráfaga corta** (p. ej. 50 avisos en 300 ms): como máximo 2 recargas.
- **Flujo sostenido** (p. ej. 1 aviso cada 0,5 s durante un minuto): una recarga cada 2 s mientras dure.

**Por qué no un debounce simple:** un debounce espera a que haya *N* ms de silencio, y el propio `debounce` de Odoo (`@web/core/utils/timing`) reinicia el temporizador en cada llamada. Con avisos cada 0,5 s y un debounce de 2 s, ese silencio no llega nunca: **la lista no se actualizaría hasta que terminara el flujo** (inanición). El throttle garantiza una latencia máxima de 2 s.

Detalles:
- **No es polling:** el temporizador solo existe cuando hay un aviso ya recibido pendiente de aplicar. Sin eventos no hay temporizadores ni peticiones.
- **Recarga:** `this.model.load()` conserva el dominio, el orden, la agrupación y la página. Además, usa `KeepLast`, así que si se solapan cargas solo se aplica la última.
- **Selección o edición en curso:** recargar crearía una lista nueva y el usuario perdería lo que está haciendo. En ese caso la recarga se aplaza (reintento local, sin RPC) hasta que termine.

### 4.3 Integración sin duplicar la interfaz

La lista de ventas declara `js_class="lyd_sale_record_realtime_list"`. Esa vista reutiliza la vista de lista nativa (`...listView`) y solo cambia:

- **El controlador:** `RealtimeListController extends ListController` añade la suscripción, el throttle y la limpieza. El template `web.ListView`, el `RelationalModel`, la paginación, la búsqueda, etc. son los nativos.
- **El renderer:** hereda de `ListRenderer`, y su template hereda `web.ListRenderer` (`t-inherit` + `xpath`) solo para insertar las tarjetas KPI encima de la tabla (patrón de `purchase_dashboard_list` del core). Las tarjetas se recalculan en `onWillUpdateProps`, así que también se actualizan en tiempo real.

Con `js_class` el comportamiento **solo afecta a esta vista**; un `patch` global de `ListController` se ejecutaría en todas las listas de Odoo.

**Cuándo sí haría falta un componente nuevo:**
- Cuando la presentación no es una lista: un feed en vivo, tarjetas animadas o un contador en la barra superior.
- Cuando hay que insertar filas de forma incremental a partir del payload, sin volver a consultar al servidor (p. ej. con volúmenes muy altos o animaciones de "nuevo registro"). Esto exigiría un modelo de datos propio.
- Cuando el componente vive fuera del sistema de vistas, como un widget de la barra de sistema.

### 4.4 Limpieza de recursos y condición de carrera

En `onWillUnmount` el controlador:
1. Llama a `bus_service.unsubscribe(tipo, callback)` con **la misma referencia** de callback con la que se suscribió (se enlaza una sola vez en `setup`).
2. Cancela el temporizador pendiente (`browser.clearTimeout`).
3. Descarta lo que estuviera pendiente.

La conexión WebSocket pertenece al servicio global: la vista solo gestiona su listener, así que no deja suscripciones huérfanas.

**Si llega un aviso justo al salir de la pantalla:**
- **Antes del unmount:** programa una recarga, pero el `clearTimeout` la cancela.
- **Después del unmount:** ya no hay listener (`unsubscribe` es síncrono y JavaScript usa un solo hilo, así que no puede colarse entre medias).
- **Con un `model.load()` ya en curso:** la guarda `status(this) === "destroyed"` impide cualquier acción posterior. Además, el ORM de un componente destruido no envía peticiones nuevas y OWL no vuelve a renderizarlo, así que es inocuo.

Al volver a la lista se crea una instancia nueva, que se suscribe de nuevo y carga datos frescos.

## 5. Pruebas

Usa una **base de datos dedicada a las pruebas** (`<base_de_pruebas>`), no la de trabajo: los tests crean y modifican registros. Desde la carpeta de Odoo:

```bash
# Con archivo de configuración
./odoo-bin -c /ruta/a/odoo.conf -d <base_de_pruebas> -i lyd_sale_record \
    --test-enable --test-tags /lyd_sale_record --stop-after-init -p <puerto_libre>

# Sin archivo de configuración
./odoo-bin --addons-path=/ruta/a/odoo/addons,/ruta/a/custom_module -d <base_de_pruebas> -i lyd_sale_record \
    --test-enable --test-tags /lyd_sale_record --stop-after-init -p <puerto_libre>
```

- **`-i lyd_sale_record`** instala el módulo si la base es nueva; si ya está instalado, usa `-u lyd_sale_record`.
- **`-p <puerto_libre>`:** un puerto que no use otro servidor de Odoo (p. ej. `8070`), porque los tests JS levantan un servidor HTTP.
- **Tests JS (hoot):** necesitan **Google Chrome o Chromium** instalado y accesible para Odoo, que los ejecuta en modo headless. Si no está disponible, Odoo omite esos tests. Para ejecutar solo los tests Python, excluye el lanzador JS: `--test-tags '/lyd_sale_record,-/lyd_sale_record:TestLydSaleRecordJs'`.

Resultado actual: **62 tests Python en verde, incluido el lanzador de los 5 tests JS (hoot), que también pasan**.

| Archivo | Qué cubre |
|---|---|
| `tests/test_lyd_sale_record.py` | Cabecera y líneas, `amount_total`, cascada, `ondelete='restrict'`, `CHECK` en la tabla de líneas, ajuste del precio unitario (creación, edición, redondeo, formulario con onchange), permisos, multicompañía, KPI |
| `tests/test_lyd_sale_record_import.py` | Formato (mensaje en inglés y en español), archivo corrupto o vacío, cabeceras, cada validación por fila, todo o nada, estados, agrupación, búsqueda y creación de relacionados (mayúsculas, archivados, logins, portal, comodines `_`/`%`, homónimos), una búsqueda por modelo sea cual sea el número de filas, búsquedas por lotes, logins distintos dentro de un mismo archivo, importador sin permisos de creación |
| `tests/test_lyd_sale_record_report.py` | Es una `VIEW` real, una fila por línea, `_depends`, agrupaciones, solo lectura |
| `tests/test_bus_notification.py` | Un aviso por lote y por importación, al canal del grupo; ninguno si la importación falla ni al editar |
| `static/tests/realtime_list.test.js` | Con tiempo simulado: recarga inmediata, ráfaga (≤ 2 recargas), flujo sostenido (varias recargas, ≤ 1 cada 2 s), limpieza al destruir la vista, aplazamiento con selección |

Para comprobar que los tests JS no pasan en falso, se rompió el código a propósito dos veces. Al quitar la limpieza de `onWillUnmount`, falla el test de limpieza. Al sustituir el throttle por un debounce, fallan 4 tests, entre ellos el de flujo sostenido. Lo mismo con la precarga: con lotes de un solo nombre (una búsqueda por nombre, como antes), el test de consultas falla (7/3/5 búsquedas en lugar de 1/1/1).

## 6. Limitaciones conocidas

- **Reimportaciones:** importar dos veces el mismo archivo **duplica las ventas**; no se detectan. Cada venta guarda el nombre del archivo de origen.
- **Mayúsculas acentuadas entre importaciones:** Odoo crea las bases de datos con `LC_COLLATE 'C'`, y así PostgreSQL no pliega mayúsculas acentuadas en `ILIKE`. Por eso "ÑANDÚ PÉREZ" en una importación posterior no encuentra a un "Ñandú Pérez" existente y lo crea de nuevo. Dentro de una misma importación sí se reconocen. Es la misma limitación del importador de facturas del core.
- **Ráfagas desde un Excel:** una importación genera un solo aviso. Las ráfagas se comprueban con los tests JS o creando registros en bucle desde `odoo-bin shell`.

## 7. Desarrollo con herramientas agénticas (Claude Code)

### 7.1 Roles

| Rol | Responsabilidad |
|---|---|
| **Arquitecto de Software / Tech Lead** (desarrollador) | Define la arquitectura, las reglas de desarrollo, los criterios de calidad y el alcance. Toma cada decisión de diseño, aprueba cada plan antes de ejecutarlo, revisa y valida los entregables y dirige el QA y la optimización. |
| **Claude Code** (herramienta de ejecución) | Redacta los documentos que se le piden, busca evidencias en el código fuente de Odoo 19, presenta opciones con esa evidencia, escribe el código y los tests, ejecuta la suite y entrega informes. No aplica ningún cambio sin la aprobación del Tech Lead. |

Artefactos de gobierno del proyecto, en la carpeta `prueba_tecnica/`:

| Archivo | Qué es |
|---|---|
| `PRUEBA_TECNICA.md` | Requisitos del PDF pasados a Markdown (fuente de verdad). |
| `REGLAS_DESARROLLO.md` | Reglas de desarrollo obligatorias. Cada una lleva **evidencia archivo:línea en el código de Odoo 19** o en las *Coding Guidelines* 19.0: nombres en inglés con el prefijo del módulo, textos traducidos con `es.po`, ORM v19 (`models.Constraint`, `_read_group`, `aggregator`…), seguridad, vistas, bus/OWL, reportes SQL y un checklist de patrones prohibidos. |
| `PLAN_DESARROLLO.md` | Plan por fases con las decisiones de diseño (D1–D16, N1–N4, M1–M8) y sus criterios de salida. |
| `.claude/settings.json` + `.claude/hooks/sync_claude_logs.sh` | Hooks (`Stop`, `SubagentStop`, `PreCompact`, `SessionEnd`) que copian las transcripciones de las sesiones a `claude_logs/` para poder auditarlas. |
| `sample_data/` | Generador y archivos Excel de prueba, y guía de pruebas manuales. |

### 7.2 Decisiones del Tech Lead

Los códigos remiten a `PLAN_DESARROLLO.md`. Cuando una opción la propuso la herramienta, la decisión de adoptarla fue igualmente del Tech Lead (p. ej. D5, D9, D10, D12–D14, D16, M4 y M5 se aprobaron tal como se propusieron).

| Área | Decisiones |
|---|---|
| **Arquitectura y datos** | **D1** nombre y prefijo del módulo (`lyd_sale_record`). **D2** cliente, vendedor y producto relacionados con los modelos del core (`res.partner`, `res.users`, `product.product`) y creados si no existen. **Refactor a Master-Detail** (cabecera + líneas). **M1** una venta por tupla normalizada (Fecha, Cliente, Vendedor, Estado). **M2** `amount_total` calculado y guardado. **M3/M7/M8** análisis sin campos duplicados en la línea, con el reporte `lyd.sale.record.report` sobre una **vista PostgreSQL real**. **M6** limpieza de los datos previos para actualizar sin migración. |
| **Reglas de negocio** | **D3** diccionario de estados y normalización con `lower()` + `strip()`. **D4** ajustar el precio unitario en lugar de rechazar la fila. **N1** creación de relacionados con `sudo()` limitada al asistente. **N2** validar siempre si el vendedor existe (incluidos los archivados) antes de crearlo. **N3/N4** marca de ajuste y precio unitario vacío. **D11** solo `.xlsx`, con el texto exacto del mensaje de error. |
| **Frontend y tiempo real** | **D6** `js_class` + subclase de `ListController`, sin efectos globales. **D7** tablero con graph, pivot y tarjetas KPI. **D8** KPI del mes actual y del filtro activo. |
| **Estándares** | Identificadores en inglés y textos traducidos con `es.po`. Verificación obligatoria de cada API contra el código fuente local de Odoo 19. **D15** sin `CLAUDE.md`: las reglas viven en `REGLAS_DESARROLLO.md`. Hooks para auditar las sesiones. |
| **Ejecución** | Delegación de la implementación en un **sub-agente ejecutor (modelo Sonnet)** que sigue el plan al pie de la letra, sin improvisar arquitectura, y devuelve un informe con evidencias. |
| **QA** | Puerta de revisión obligatoria antes de la fase de pruebas. Ajustes manuales de las vistas. Exigencia de que ningún test pase en falso (pruebas de mutación). Aprobación previa de cada corrección antes de aplicarla. Pruebas manuales con los Excel de `sample_data/`. |
| **Optimización** | Precarga de la caché del asistente con un diseño definido: extraer los nombres únicos del Excel, normalizarlos con `_cache_key`, buscarlos antes de crear las ventas y usar esas búsquedas como caché. Aplicación de DRY en todo el código repetido. Aprobación del ajuste propuesto (`dict` en lugar de `set`, para conservar la escritura original de los nombres). |

### 7.3 Flujo de trabajo con puertas de aprobación

Cada fase siguió el mismo ciclo: **propuesta con evidencia → decisión del Tech Lead → ejecución → verificación → validación del Tech Lead**.

1. **Requisitos:** el PDF se pasó a Markdown como fuente de verdad.
2. **Reglas y plan:** el Tech Lead fijó los estándares y resolvió las decisiones en varias iteraciones (D, N y después M) hasta aprobar el plan. Nada se implementó antes de esa aprobación.
3. **Ejecución:** el sub-agente implementó las fases aprobadas y se detuvo antes de las pruebas, como había indicado el Tech Lead.
4. **Revisión:** el código entregado se contrastó con el plan y las reglas. El Tech Lead ajustó las vistas y pidió completar las traducciones.
5. **QA:** se diseñó y ejecutó la suite de la Fase 6. Las correcciones se propusieron y solo se aplicaron tras su aprobación.
6. **Optimización:** el Tech Lead encargó la precarga de la caché y el DRY, revisó el análisis y el plan y aprobó su ejecución.

### 7.4 Supervisión y ajustes durante el desarrollo

- **Auditoría Estricta y Control del Agente:** Se exigió evidencia del código fuente de Odoo 19 para auditar las propuestas de la IA antes de implementarlas, logrando:
  - Cumplimiento v19: Transición forzada de `_sql_constraints` a `models.Constraint`.
  - Rendimiento UI: Sustitución de un `debounce` defectuoso por un throttle para flujos sostenidos.
  - Seguridad: Uso de `res.groups` como canal seguro del bus y limitación de permisos en la creación de contactos/productos.
  - Corrección de Alucinaciones: Detección y corrección de afirmaciones erróneas del modelo (ej. restricciones ficticias sobre tildes en logins).
- **Defectos encontrados por la suite y la revisión**, corregidos tras la aprobación del Tech Lead:
  - La marca de precio ajustado se perdía en el formulario (el onchange se volvía a ejecutar).
  - `_` y `%` funcionaban como comodines en la búsqueda por nombre.
  - Se duplicaban vendedores con mayúsculas acentuadas dentro de una importación.
  - Faltaba `currency_id` en las listas (los importes salían sin símbolo de moneda).
- **Tests que no pasan en falso:** el código se rompió a propósito para comprobar que los tests fallan. Así se descubrió que un test de limpieza pasaba aunque se quitara la limpieza (el ORM de un componente destruido ya no envía peticiones) y se reescribió para observar el listener y el temporizador directamente. La precarga de la caché se verificó igual.
- **Escalabilidad, Rendimiento y Refactorización:** Intervine la arquitectura de importación para soportar cargas masivas, sustituyendo las búsquedas iterativas de la IA por un algoritmo de precarga en caché (reduciendo las llamadas al ORM de 1.350 a 3 en escenarios críticos). Paralelamente, impuse estándares de código limpio (DRY) refactorizando tres métodos redundantes en uno solo, unificando validaciones y extrayendo lógicas complejas de KPI. Estas decisiones estructurales fueron certificadas exitosamente mediante 62 tests automatizados y simulaciones de importación pesadas.
