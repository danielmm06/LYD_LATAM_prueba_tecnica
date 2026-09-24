# Datos de prueba — guía de pruebas manuales (`lyd_sale_record`)

Los archivos se generan con `generate_sample_data.py`:

```bash
cd /Users/daniel/Documents/proyectos_odoo/odoo_19
venv/bin/python custom_addons/LYD_LATAM_prueba_tecnica/prueba_tecnica/sample_data/generate_sample_data.py
```

> Las filas "del mes actual" usan la fecha del día en que se ejecuta el script. Si repites las pruebas otro mes, **regenera los archivos** para que las tarjetas "este mes" cuadren con los valores de abajo.
> Los resultados esperados se obtuvieron pasando cada archivo por el wizard real (con rollback) sobre `lyd_prueba` **vacía** e idioma `es_CO`.

## Preparación

1. Reinicia el servidor (puerto 19000) para cargar la versión `19.0.1.1.0` del módulo.
2. BD `lyd_prueba` **sin ventas**. Si ya importaste antes, borra las ventas desde *Ventas* (hace falta el nivel *Gerente*). Los clientes, vendedores y productos que ya existan se reutilizan, así que el número de "nuevos" del mensaje saldrá menor.
3. Para la prueba de tiempo real necesitas **dos usuarios** con acceso al módulo (privilegio *Registro de venta*, nivel *Usuario* o *Gerente*): por ejemplo `admin` (ya es *Gerente*) y el usuario `test`. Asígnaselo en *Ajustes → Usuarios*.

## Orden de las pruebas y resultado esperado

| # | Archivo | Qué prueba | Resultado esperado |
|---|---|---|---|
| 1 | `sales_sample_unsupported_format.csv` | D11: formato no soportado | Error: *"Formato no soportado. Por favor, cargue un archivo con extensión .xlsx"*. No se crea nada. |
| 2 | `sales_sample_missing_column.xlsx` | Cabecera incompleta | Error: *"Al archivo Excel le faltan las siguientes columnas: Valor Total."* |
| 3 | `sales_sample_with_errors.xlsx` | Una fila por validación + 1 fila válida (todo o nada, D5) | Error: *"No se pudo importar el archivo. Se encontraron 15 error(es):"* + la lista por fila y columna. **No se crea ninguna venta**, tampoco la de la fila válida. La hoja *"Casos de error"* del archivo explica cada fila. |
| 4 | `sales_sample.xlsx` | Importación principal | *"37 ventas con 39 líneas importadas. Nuevos clientes: 6, vendedores: 4, productos: 5. Precio unitario ajustado en 3 líneas."* |
| 5 | `sales_sample_second_import.xlsx` | Segunda importación: tiempo real + reutilización | *"4 ventas con 5 líneas importadas. Nuevos clientes: 1, vendedores: 2, productos: 1. Precio unitario ajustado en 1 líneas."* |

> ⚠️ Importar dos veces el mismo archivo **duplica las ventas** (D16: no se detectan reimportaciones).

### Qué revisar después del paso 4 (`sales_sample.xlsx`)

- **Agrupación (M1):** la venta del **2026-07-01** de *Cliente A* / *Juan Pérez* tiene **3 líneas** (Producto 1, 2 y 3) y un total de **325.000**. Una de sus filas escribe el cliente como "cliente a" y aun así se agrupa.
- **Ajuste de precio unitario (D4/N4)**, en el formulario de la venta o en el Tablero con el filtro *Precio unitario ajustado*:
  - 2026-06-02, Producto 1: 2 × 50.000 ≠ 110.000 → precio unitario **55.000**.
  - 2026-06-03, Producto 3: sin valor unitario, total 105.000 / 3 → **35.000**.
  - 2026-06-04, Producto 2: 3 × 30.000 ≠ 100.000 → **33.333,33**.
- **Estados (D3):** "CONFIRMADA", "  borrador  " y "confirmed" se importan como *Confirmada*, *Borrador* y *Confirmada*.
- **Vendedores creados (N2):** en *Ajustes → Usuarios* aparecen `juan.perez`, `maria.gomez`, `carlos.rodriguez` y `ana.martinez`, sin contraseña.
- **Tarjetas KPI** (lista *Ventas*): *Total vendido en el mes* **1.265.000**, *Ventas del mes* **6**; con el filtro vacío, **17.025.750** y **37** ventas.
- **Tablero** (graph y pivot sobre el reporte SQL): 39 líneas. Agrupa por producto, cliente, vendedor, estado y mes; la suma total es 17.025.750.

### Paso 5: prueba de tiempo real (dos navegadores)

1. **Navegador A** (p. ej. `admin`): abre *Ventas* y déjala abierta.
2. **Navegador B** (p. ej. `test`, en otra ventana privada o en otro navegador): *Importar Excel* → `sales_sample_second_import.xlsx`.
3. En **A, sin recargar**, deben aparecer **4 ventas nuevas** con fecha de hoy, y las tarjetas deben pasar a *Total vendido en el mes* **2.000.000** / *Ventas del mes* **10** (y **17.760.750** / **41** sin filtro).
4. Qué comprueba este archivo:
   - "  CLIENTE A " (con espacios y en mayúsculas) **reutiliza** *Cliente A* y sus 2 filas forman **una venta de 2 líneas**.
   - *Cliente G*, *Laura Sánchez* (login `laura.sanchez`) y *Producto 6* **se crean**.
   - "Juan Perez" (sin tilde) es un nombre distinto de "Juan Pérez", así que se crea otro vendedor. Como `juan.perez` ya está ocupado, su login es **`juan.perez.2`**.
   - Línea de *Cliente C*: 4 × 35.000 ≠ 120.000 → precio unitario ajustado a **30.000**.

### Otras comprobaciones manuales

- **Limpieza de listeners:** en A, sal de *Ventas* (a otro menú) y repite el paso 2 en B con otro archivo válido. En las herramientas de desarrollador de A (pestaña *Red*) no debe aparecer ningún `web_search_read` de `lyd.sale.record`. Al volver a *Ventas*, los datos están al día.
- **Selección en curso:** en A marca una o varias ventas y deja la selección activa mientras B importa. La lista **no** se recarga, así que no pierdes la selección. Al desmarcarlas, se recarga en ≤ 2 s.
- **Ráfagas / flujo sostenido:** necesitan muchas creaciones seguidas y no se pueden hacer con un Excel (cada importación envía **un solo** aviso). Se prueban en la Fase 6 con un script de `odoo-bin shell`.
