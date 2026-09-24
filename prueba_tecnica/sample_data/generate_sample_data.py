"""Generate the sample Excel files used to test the ``lyd_sale_record`` import wizard.

Usage (from any directory, with the Odoo venv):

    python generate_sample_data.py

Files written next to this script:

- ``sales_sample.xlsx``: valid file, imports without errors. It covers the
  functional cases of the import (see the ``CASES`` notes below).
- ``sales_sample_with_errors.xlsx``: one row per validation rule; the import must
  be rejected as a whole (all or nothing) listing every error. A second sheet
  describes the expected error of each row.
- ``sales_sample_missing_column.xlsx``: valid rows but without the "Valor Total"
  column; the import must be rejected with a header error.
- ``sales_sample_second_import.xlsx``: second valid import (current month) for the
  manual real-time test; it reuses and creates related records (see its notes).
- ``sales_sample_unsupported_format.csv``: rejected with the "Unsupported format"
  message (D11).

The manual test guide is ``README.md`` in this folder.

Amounts are written as literal values on purpose (not formulas): the wizard reads
cached values (``data_only=True``) and the unit-price adjustment rule (D4) needs
rows whose total does not match quantity x unit price.
"""

import csv
import random
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUTPUT_DIR = Path(__file__).resolve().parent

# Excel contract defined by the requirements document (PRUEBA_TECNICA.md).
HEADERS = [
    "Fecha", "Cliente", "Vendedor", "Producto",
    "Cantidad", "Valor Unitario", "Valor Total", "Estado",
]

CUSTOMERS = ["Cliente A", "Cliente B", "Cliente C", "Cliente D", "Cliente E", "Cliente F"]
SALESPEOPLE = ["Juan Pérez", "María Gómez", "Carlos Rodríguez", "Ana Martínez"]
PRODUCTS = {
    "Producto 1": 50000,
    "Producto 2": 120000,
    "Producto 3": 35000,
    "Producto 4": 250000,
    "Producto 5": 8500,
}
STATES = ["Confirmada", "Confirmada", "Confirmada", "Borrador", "Cancelada"]

FONT = Font(name="Arial", size=10)
HEADER_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", start_color="4F6D7A")
DATE_FORMAT = "yyyy-mm-dd"
AMOUNT_FORMAT = "#,##0"


def _style_sheet(sheet, widths):
    for cell in sheet[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = FONT
    for column_letter, width in widths.items():
        sheet.column_dimensions[column_letter].width = width
    sheet.freeze_panes = "A2"


def _write_sales_sheet(sheet, headers, rows):
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            header = headers[cell.column - 1]
            if header == "Fecha" and isinstance(cell.value, date):
                cell.number_format = DATE_FORMAT
            elif header in ("Valor Unitario", "Valor Total") and isinstance(cell.value, (int, float)):
                cell.number_format = AMOUNT_FORMAT
    widths = {"A": 13, "B": 14, "C": 20, "D": 13, "E": 11, "F": 16, "G": 14, "H": 13}
    _style_sheet(sheet, {k: v for k, v in widths.items() if ord(k) - 64 <= len(headers)})


def build_valid_rows():
    """30 rows in 2026-06 (the month of the requirements example) + 6 rows in the
    current month, so both KPI cards (current month / active filter) show data."""
    rng = random.Random(19)  # deterministic output
    rows = []
    for index in range(30):
        product = rng.choice(list(PRODUCTS))
        quantity = rng.randint(1, 10)
        price_unit = PRODUCTS[product]
        rows.append([
            date(2026, 6, 1 + index % 30),
            rng.choice(CUSTOMERS),
            rng.choice(SALESPEOPLE),
            product,
            quantity,
            price_unit,
            quantity * price_unit,
            rng.choice(STATES),
        ])

    # Exact row of the requirements document example.
    rows[0] = [date(2026, 6, 1), "Cliente A", "Juan Pérez", "Producto 1", 2, 50000, 100000, "Confirmada"]

    # Functional cases (all valid; they must be imported):
    # D4 - total does not match quantity x unit price -> unit price adjusted to 110000 / 2 = 55000.
    rows[1] = [date(2026, 6, 2), "Cliente B", "María Gómez", "Producto 1", 2, 50000, 110000, "Confirmada"]
    # N4 - empty unit price -> computed as 105000 / 3 = 35000 and flagged as adjusted.
    rows[2] = [date(2026, 6, 3), "Cliente C", "Carlos Rodríguez", "Producto 3", 3, None, 105000, "Confirmada"]
    # D4 with a non-exact division -> 100000 / 3 = 33333.33...
    rows[3] = [date(2026, 6, 4), "Cliente D", "Ana Martínez", "Producto 2", 3, 30000, 100000, "Borrador"]
    # D3 - status normalization (upper case and surrounding spaces).
    rows[4] = [date(2026, 6, 5), "Cliente E", "Juan Pérez", "Producto 4", 1, 250000, 250000, "CONFIRMADA"]
    rows[5] = [date(2026, 6, 6), "Cliente F", "María Gómez", "Producto 5", 4, 8500, 34000, "  borrador  "]
    # D3 - technical key accepted as status.
    rows[6] = [date(2026, 6, 7), "Cliente A", "Carlos Rodríguez", "Producto 2", 1, 120000, 120000, "confirmed"]
    # D2 - same customer / salesperson / product with different case -> reused, not duplicated.
    rows[7] = [date(2026, 6, 8), "cliente a", "juan pérez", "producto 1", 5, 50000, 250000, "Confirmada"]
    # Date given as text in YYYY-MM-DD format.
    rows[8] = ["2026-06-09", "Cliente B", "Ana Martínez", "Producto 3", 2, 35000, 70000, "Cancelada"]
    # Decimal quantity.
    rows[9] = [date(2026, 6, 10), "Cliente C", "Juan Pérez", "Producto 5", 2.5, 8500, 21250, "Confirmada"]

    # M1 - three rows sharing the same (date, customer, salesperson, status) tuple
    # must be grouped into a single sale with 3 lines. One row spells the customer
    # in lower case ("cliente a") to show that the grouping key is normalized with
    # strip().lower(), so it still joins the same sale as "Cliente A".
    rows.append([date(2026, 7, 1), "Cliente A", "Juan Pérez", "Producto 1", 2, 50000, 100000, "Confirmada"])
    rows.append([date(2026, 7, 1), "cliente a", "Juan Pérez", "Producto 2", 1, 120000, 120000, "Confirmada"])
    rows.append([date(2026, 7, 1), "Cliente A", "Juan Pérez", "Producto 3", 3, 35000, 105000, "Confirmada"])

    today = date.today()
    for day, (customer, salesperson, product, quantity, state) in enumerate([
        ("Cliente A", "Juan Pérez", "Producto 1", 3, "Confirmada"),
        ("Cliente B", "María Gómez", "Producto 2", 1, "Confirmada"),
        ("Cliente C", "Carlos Rodríguez", "Producto 4", 2, "Borrador"),
        ("Cliente D", "Ana Martínez", "Producto 3", 6, "Confirmada"),
        ("Cliente E", "Juan Pérez", "Producto 5", 10, "Cancelada"),
        ("Cliente F", "María Gómez", "Producto 1", 4, "Confirmada"),
    ], start=1):
        price_unit = PRODUCTS[product]
        rows.append([
            today.replace(day=min(day, today.day)), customer, salesperson, product,
            quantity, price_unit, quantity * price_unit, state,
        ])
    return rows


# (row values, expected error) - one validation rule per row.
ERROR_CASES = [
    ([None, "Cliente A", "Juan Pérez", "Producto 1", 1, 50000, 50000, "Confirmada"],
     'Fecha vacía -> "Invalid date"'),
    (["31/02/2026", "Cliente A", "Juan Pérez", "Producto 1", 1, 50000, 50000, "Confirmada"],
     'Fecha con formato inválido (no YYYY-MM-DD) -> "Invalid date"'),
    ([date(2026, 6, 3), None, "Juan Pérez", "Producto 1", 1, 50000, 50000, "Confirmada"],
     'Cliente vacío -> "This field is required"'),
    ([date(2026, 6, 4), "Cliente A", None, "Producto 1", 1, 50000, 50000, "Confirmada"],
     'Vendedor vacío -> "This field is required"'),
    ([date(2026, 6, 5), "Cliente A", "Juan Pérez", "   ", 1, 50000, 50000, "Confirmada"],
     'Producto solo con espacios -> "This field is required"'),
    ([date(2026, 6, 6), "Cliente A", "Juan Pérez", "Producto 1", 0, 50000, 50000, "Confirmada"],
     'Cantidad = 0 -> "Expected a number greater than zero"'),
    ([date(2026, 6, 7), "Cliente A", "Juan Pérez", "Producto 1", -2, 50000, 50000, "Confirmada"],
     'Cantidad negativa -> "Expected a number greater than zero"'),
    ([date(2026, 6, 8), "Cliente A", "Juan Pérez", "Producto 1", "dos", 50000, 100000, "Confirmada"],
     'Cantidad no numérica -> "Expected a number greater than zero"'),
    ([date(2026, 6, 9), "Cliente A", "Juan Pérez", "Producto 1", 1, 50000, 0, "Confirmada"],
     'Valor Total = 0 -> "Expected a number greater than zero"'),
    ([date(2026, 6, 10), "Cliente A", "Juan Pérez", "Producto 1", 1, 50000, -50000, "Confirmada"],
     'Valor Total negativo -> "Expected a number greater than zero"'),
    ([date(2026, 6, 11), "Cliente A", "Juan Pérez", "Producto 1", 1, "abc", 50000, "Confirmada"],
     'Valor Unitario no numérico -> "Expected a number"'),
    ([date(2026, 6, 12), "Cliente A", "Juan Pérez", "Producto 1", 1, 50000, 50000, None],
     'Estado vacío -> "This field is required"'),
    ([date(2026, 6, 13), "Cliente A", "Juan Pérez", "Producto 1", 1, 50000, 50000, "Pagada"],
     'Estado desconocido -> "Unknown status"'),
    ([date(2026, 6, 14), "Cliente A", "Juan Pérez", "Producto 1", 1, 50000, "#DIV/0!", "Confirmada"],
     'Celda con valor de error de Excel -> "The cell contains an error value"'),
    ([date(2026, 6, 15), "Cliente A", "Juan Pérez", "Producto 1", 2, 50000, 100000, "Confirmada"],
     "Fila VÁLIDA: no debe crearse porque el archivo tiene errores (todo o nada, D5)"),
]


def write_valid_file():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ventas"
    _write_sales_sheet(sheet, HEADERS, build_valid_rows())
    path = OUTPUT_DIR / "sales_sample.xlsx"
    workbook.save(path)
    return path


def write_errors_file():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ventas"
    _write_sales_sheet(sheet, HEADERS, [values for values, _expected in ERROR_CASES])

    # Second sheet: the wizard only reads the first one.
    notes = workbook.create_sheet("Casos de error")
    notes.append(["Fila", "Caso probado / error esperado"])
    for row_number, (_values, expected) in enumerate(ERROR_CASES, start=2):
        notes.append([row_number, expected])
    _style_sheet(notes, {"A": 8, "B": 90})

    path = OUTPUT_DIR / "sales_sample_with_errors.xlsx"
    workbook.save(path)
    return path


def write_missing_column_file():
    headers = [header for header in HEADERS if header != "Valor Total"]
    rows = [
        [date(2026, 6, 1), "Cliente A", "Juan Pérez", "Producto 1", 2, 50000, "Confirmada"],
        [date(2026, 6, 2), "Cliente B", "María Gómez", "Producto 2", 1, 120000, "Borrador"],
    ]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ventas"
    _write_sales_sheet(sheet, headers, rows)
    path = OUTPUT_DIR / "sales_sample_missing_column.xlsx"
    workbook.save(path)
    return path


def build_second_import_rows():
    """Rows for the manual real-time test: import this file from a second browser
    session while another user watches the "Sale Records" list. All dates are in
    the current month, so the "this month" KPI cards change visibly."""
    today = date.today()
    current_day = today.day
    return [
        # M1 - two rows with the same tuple -> one sale with 2 lines. The customer is
        # written with extra spaces and upper case: it reuses the existing "Cliente A".
        [today.replace(day=current_day), "  CLIENTE A ", "María Gómez", "Producto 2", 2, 120000, 240000, "Confirmada"],
        [today.replace(day=current_day), "Cliente A", "María Gómez", "Producto 4", 1, 250000, 250000, "Confirmada"],
        # D2/N1 - new customer, new salesperson and new product -> all three are created.
        # The salesperson login is generated as "laura.sanchez".
        [today.replace(day=current_day), "Cliente G", "Laura Sánchez", "Producto 6", 5, 15000, 75000, "Borrador"],
        # N2 - "Juan Perez" (without accent) is a different name from the existing
        # "Juan Pérez", so a new salesperson is created; its login "juan.perez" is
        # already taken, so it gets the suffix -> "juan.perez.2".
        [today.replace(day=current_day), "Cliente B", "Juan Perez", "Producto 1", 1, 50000, 50000, "Confirmada"],
        # D4 - total does not match quantity x unit price -> unit price adjusted to 30000.
        [today.replace(day=current_day), "Cliente C", "Ana Martínez", "Producto 3", 4, 35000, 120000, "Cancelada"],
    ]


def write_second_import_file():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ventas"
    _write_sales_sheet(sheet, HEADERS, build_second_import_rows())
    path = OUTPUT_DIR / "sales_sample_second_import.xlsx"
    workbook.save(path)
    return path


def write_unsupported_format_file():
    """Same data as a valid file but saved as CSV: the wizard must reject it with
    the D11 message ("Unsupported format...")."""
    path = OUTPUT_DIR / "sales_sample_unsupported_format.csv"
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(HEADERS)
        writer.writerow(["2026-06-01", "Cliente A", "Juan Pérez", "Producto 1", 2, 50000, 100000, "Confirmada"])
    return path


if __name__ == "__main__":
    for written in (
        write_valid_file(),
        write_errors_file(),
        write_missing_column_file(),
        write_second_import_file(),
        write_unsupported_format_file(),
    ):
        print(f"Written: {written}")
