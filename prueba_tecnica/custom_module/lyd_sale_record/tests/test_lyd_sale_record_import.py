# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import Counter
from contextlib import ExitStack
from datetime import date, datetime
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.lyd_sale_record.wizard import lyd_sale_record_import as import_wizard

from .common import HEADERS, LydSaleRecordCommon


@tagged('post_install', '-at_install')
class TestLydSaleRecordImport(LydSaleRecordCommon):

    def _assert_import_error(self, rows=None, expected=(), **kwargs):
        """Import must fail with a UserError containing every ``expected`` text,
        and must not create anything (all or nothing, D5)."""
        counts_before = self._counts()
        with self.assertRaises(UserError) as error:
            self._import(rows, **kwargs)
        message = error.exception.args[0]
        for text in expected:
            self.assertIn(text, message)
        self.assertEqual(self._counts(), counts_before)
        return message

    def _counts(self):
        return {
            model: self.env[model].with_context(active_test=False).search_count([])
            for model in ('lyd.sale.record', 'lyd.sale.record.line', 'res.partner', 'res.users', 'product.product')
        }

    # ------------------------------------------------------------------
    # File format (D11) and header
    # ------------------------------------------------------------------

    def test_unsupported_format(self):
        for file_name in ('sales.csv', 'sales.xls', 'sales.pdf', 'sales', False):
            with self.subTest(file_name=file_name):
                self._assert_import_error(
                    [self._row()], file_name=file_name,
                    expected=["Unsupported format. Please upload a file with the .xlsx extension."],
                )

    def test_unsupported_format_message_is_translated(self):
        self._assert_import_error(
            [self._row()], file_name='sales.csv', lang='es_CO',
            expected=["Formato no soportado. Por favor, cargue un archivo con extensión .xlsx"],
        )

    def test_extension_is_case_insensitive(self):
        self._import([self._row()], file_name='SALES.XLSX')
        self.assertEqual(self.env['lyd.sale.record'].search_count([('import_file_name', '=', 'SALES.XLSX')]), 1)

    def test_corrupted_file(self):
        self._assert_import_error(
            file_content=base64.b64encode(b"this is not an excel file"),
            expected=["The file could not be read"],
        )

    def test_empty_file(self):
        self._assert_import_error([], headers=None, expected=["The Excel file has no rows."])

    def test_header_without_data(self):
        self._assert_import_error([], expected=["The Excel file has no data rows."])

    def test_missing_columns(self):
        headers = [header for header in HEADERS if header not in ("Valor Total", "Estado")]
        self._assert_import_error(
            [["2026-06-01", "A", "B", "C", 1, 1]], headers=headers,
            expected=["The Excel file is missing the following columns: Valor Total, Estado."],
        )

    def test_header_order_case_and_spaces_are_ignored(self):
        headers = ["  ESTADO ", "valor total", "Valor Unitario", "cantidad", "PRODUCTO", "Vendedor", "cliente", "Fecha"]
        row = self._row()
        self._import([list(reversed(row))], headers=headers)
        line = self.env['lyd.sale.record'].search([], order='id desc', limit=1).line_ids
        self.assertEqual((line.quantity, line.price_total), (2, 100000))

    # ------------------------------------------------------------------
    # Row validations
    # ------------------------------------------------------------------

    def test_row_validations(self):
        cases = [
            ({'date': None}, 'column "Fecha": Invalid date'),
            ({'date': "31/02/2026"}, 'column "Fecha": Invalid date'),
            ({'date': "2026-13-40"}, 'column "Fecha": Invalid date'),
            ({'customer': None}, 'column "Cliente": This field is required.'),
            ({'customer': "   "}, 'column "Cliente": This field is required.'),
            ({'salesperson': None}, 'column "Vendedor": This field is required.'),
            ({'product': "  "}, 'column "Producto": This field is required.'),
            ({'quantity': 0}, 'column "Cantidad": Expected a number greater than zero.'),
            ({'quantity': -2}, 'column "Cantidad": Expected a number greater than zero.'),
            ({'quantity': "two"}, 'column "Cantidad": Expected a number greater than zero.'),
            ({'quantity': None}, 'column "Cantidad": Expected a number greater than zero.'),
            ({'price_total': 0}, 'column "Valor Total": Expected a number greater than zero.'),
            ({'price_total': -100}, 'column "Valor Total": Expected a number greater than zero.'),
            ({'price_unit': "abc"}, 'column "Valor Unitario": Expected a number.'),
            ({'state': None}, 'column "Estado": This field is required.'),
            ({'state': "Pagada"}, 'column "Estado": Unknown status'),
            ({'price_total': "#DIV/0!"}, 'column "Valor Total": The cell contains an error value.'),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                self._assert_import_error([self._row(), self._row(**overrides)], expected=[f"Row 3, {expected}"])

    def test_all_errors_are_reported_at_once(self):
        message = self._assert_import_error([
            self._row(customer=None),
            self._row(),
            self._row(quantity=0, state="Pagada"),
        ], expected=[
            "3 error(s) were found",
            'Row 2, column "Cliente"',
            'Row 4, column "Cantidad"',
            'Row 4, column "Estado"',
        ])
        self.assertNotIn("Row 3", message)

    def test_error_list_is_truncated(self):
        self._assert_import_error(
            [self._row(quantity=0) for _i in range(60)],
            expected=["60 error(s) were found", "Row 51, ", "...and 10 more"],
        )

    def test_valid_rows_are_not_imported_when_another_row_fails(self):
        """All or nothing (D5): no sale, line, customer, salesperson or product is created."""
        self._assert_import_error([
            self._row(customer="Brand New Customer", salesperson="Brand New Salesperson", product="Brand New Product"),
            self._row(price_total=-1),
        ])

    def test_empty_rows_are_skipped(self):
        self._import([self._row(), [None] * 8, self._row(date=date(2026, 6, 2))])
        self.assertEqual(self.env['lyd.sale.record'].search_count([('import_file_name', '=', 'sales.xlsx')]), 2)

    def test_date_formats(self):
        self._import([
            self._row(date=datetime(2026, 6, 1, 15, 30)),
            self._row(date="2026-06-02", customer="Other Customer"),
        ])
        dates = self.env['lyd.sale.record'].search([('import_file_name', '=', 'sales.xlsx')]).mapped('date')
        self.assertEqual(sorted(dates), [date(2026, 6, 1), date(2026, 6, 2)])

    # ------------------------------------------------------------------
    # Status mapping (D3)
    # ------------------------------------------------------------------

    def test_status_normalization(self):
        cases = {
            "Borrador": 'draft', "CONFIRMADA": 'confirmed', "  cancelada  ": 'cancelled',
            "draft": 'draft', "Confirmed": 'confirmed', " CANCELLED ": 'cancelled',
        }
        for raw_state, expected_state in cases.items():
            with self.subTest(raw_state=raw_state):
                self._import([self._row(state=raw_state)], file_name=f'{expected_state}.xlsx')
                sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
                self.assertEqual(sale.state, expected_state)

    # ------------------------------------------------------------------
    # Grouping rows into sales (M1)
    # ------------------------------------------------------------------

    def test_rows_with_same_tuple_are_grouped_into_one_sale(self):
        result = self._import([
            self._row(product="Product A"),
            self._row(date=date(2026, 6, 5)),  # other sale in between
            self._row(customer="  existing CUSTOMER ", salesperson="EXISTING salesperson", product="Product B"),
            self._row(product="Product C", state="Borrador"),  # same people/date, other status
        ])
        sales = self.env['lyd.sale.record'].search([('import_file_name', '=', 'sales.xlsx')])
        self.assertEqual(len(sales), 3)
        grouped = sales.filtered(lambda s: s.date == date(2026, 6, 1) and s.state == 'confirmed')
        self.assertEqual(grouped.line_ids.product_id.mapped('name'), ["Product A", "Product B"])
        self.assertEqual(grouped.partner_id, self.partner)
        self.assertEqual(grouped.user_id, self.salesperson)
        self.assertEqual(grouped.amount_total, 200000)
        self.assertIn("3 sales with 4 lines imported", result['params']['message'])

    # ------------------------------------------------------------------
    # Related records: find or create (D2 / N1 / N2)
    # ------------------------------------------------------------------

    def test_existing_records_are_reused_ignoring_case(self):
        counts_before = self._counts()
        self._import([self._row(customer="EXISTING customer", salesperson="existing SALESPERSON", product="existing product")])
        sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
        self.assertEqual((sale.partner_id, sale.user_id, sale.line_ids.product_id), (self.partner, self.salesperson, self.product))
        counts_after = self._counts()
        for model in ('res.partner', 'res.users', 'product.product'):
            self.assertEqual(counts_after[model], counts_before[model], model)

    def test_new_records_are_created_once(self):
        result = self._import([
            self._row(customer="New Customer", salesperson="Ñandú Pérez", product="New Product"),
            self._row(customer="new customer", salesperson="ÑANDÚ PÉREZ", product="NEW PRODUCT", date=date(2026, 6, 2)),
        ])
        partner = self.env['res.partner'].search([('name', '=', "New Customer")])
        user = self.env['res.users'].search([('name', '=', "Ñandú Pérez")])
        product = self.env['product.product'].search([('name', '=', "New Product")])
        self.assertEqual((len(partner), len(user), len(product)), (1, 1, 1))
        self.assertEqual(user.login, 'nandu.perez')
        self.assertFalse(user.share)
        self.assertIn("New customers: 1, salespeople: 1, products: 1", result['params']['message'])

    def test_archived_salesperson_is_reused(self):
        self.salesperson.active = False
        users_before = self._counts()['res.users']
        self._import([self._row()])
        sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
        self.assertEqual(sale.user_id, self.salesperson)
        self.assertEqual(self._counts()['res.users'], users_before)

    def test_active_salesperson_is_preferred_over_archived_homonym(self):
        archived = new_test_user(self.env, login='homonym.archived', name="Homonym Salesperson")
        archived.active = False
        active = new_test_user(self.env, login='homonym.active', name="Homonym Salesperson")
        self._import([self._row(salesperson="Homonym Salesperson")])
        sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
        self.assertEqual(sale.user_id, active)

    def test_generated_login_skips_taken_logins_including_archived(self):
        # names unlikely to exist in the database, so the test does not depend on its data
        new_test_user(self.env, login='zoe.lydtest', name="Other Zoe")
        archived = new_test_user(self.env, login='zoe.lydtest.2', name="Another Zoe")
        archived.active = False
        self._import([self._row(salesperson="Zoé Lydtest")])
        user = self.env['res.users'].search([('name', '=', "Zoé Lydtest")])
        self.assertEqual(user.login, 'zoe.lydtest.3')

    def test_portal_user_is_not_used_as_salesperson(self):
        portal = new_test_user(self.env, login='portal.homonym', name="Portal Homonym", groups='base.group_portal')
        self._import([self._row(salesperson="Portal Homonym")])
        sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
        self.assertNotEqual(sale.user_id, portal)
        self.assertFalse(sale.user_id.share)

    def test_wildcard_characters_do_not_match_other_records(self):
        """``_`` and ``%`` in a name must be matched literally, not as SQL wildcards."""
        self._import([self._row(customer="Existing_Customer", salesperson="Existing%", product="Existing_Product")])
        sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
        self.assertNotEqual(sale.partner_id, self.partner)
        self.assertNotEqual(sale.user_id, self.salesperson)
        self.assertNotEqual(sale.line_ids.product_id, self.product)

    def _count_name_searches(self, rows):
        """Import ``rows`` and return the number of name searches (``=ilike``) per model."""
        searches = Counter()
        with ExitStack() as stack:
            for model_name in ('res.partner', 'res.users', 'product.product'):
                model_class = self.env.registry[model_name]

                def search(model, domain, *args, _original_search=model_class.search, **kwargs):
                    if "=ilike" in repr(domain):
                        searches[model._name] += 1
                    return _original_search(model, domain, *args, **kwargs)

                stack.enter_context(patch.object(model_class, 'search', search))
            self._import(rows)
        return searches

    def test_related_records_are_searched_once_per_model(self):
        """The unique names of the file are searched in one query per model,
        whatever the number of rows (cache prefetch)."""
        def rows(count):
            return [
                self._row(customer=f"Bulk Customer {i % 7}", salesperson=f"Bulk Salesperson {i % 3}",
                          product=f"Bulk Product {i % 5}", date=date(2026, 6, 1 + i % 28))
                for i in range(count)
            ]
        expected = {'res.partner': 1, 'res.users': 1, 'product.product': 1}
        self.assertEqual(dict(self._count_name_searches(rows(20))), expected)
        self.assertEqual(dict(self._count_name_searches(rows(40))), expected)
        self.assertEqual(len(self.env['res.partner'].search([('name', '=like', "Bulk Customer %")])), 7)

    def test_name_searches_are_split_in_batches(self):
        self.startPatcher(patch.object(import_wizard, 'SEARCH_BATCH_SIZE', 2))
        searches = self._count_name_searches([
            self._row(customer=f"Batch Customer {i}") for i in range(5)
        ])
        self.assertEqual(searches['res.partner'], 3)  # 2 + 2 + 1 names
        self.assertEqual(len(self.env['res.partner'].search([('name', '=like', "Batch Customer %")])), 5)

    def test_new_salespeople_of_one_file_get_distinct_logins(self):
        # different names (so two users), same base login once the accents are removed
        self._import([
            self._row(salesperson="Zoé Lydtest"),
            self._row(salesperson="Zoe Lydtest", date=date(2026, 6, 2)),
        ])
        users = self.env['res.users'].search([('name', 'in', ["Zoé Lydtest", "Zoe Lydtest"])])
        self.assertEqual(sorted(users.mapped('login')), ['zoe.lydtest', 'zoe.lydtest.2'])

    def test_homonym_customer_follows_the_default_order(self):
        """Among homonyms, the record chosen is the first one in the model order,
        as with the previous one-by-one search (res.partner: ``id DESC``)."""
        self.env['res.partner'].create({'name': "Homonym Customer"})
        newest = self.env['res.partner'].create({'name': "Homonym Customer"})
        self._import([self._row(customer="Homonym Customer")])
        sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
        self.assertEqual(sale.partner_id, newest)

    # ------------------------------------------------------------------
    # Unit price adjustment through the import (D4 / N4)
    # ------------------------------------------------------------------

    def test_import_adjusts_unit_prices(self):
        result = self._import([
            self._row(quantity=2, price_unit=50000, price_total=110000),
            self._row(quantity=3, price_unit=None, price_total=105000, product="Other Product"),
            self._row(quantity=2, price_unit=50000, price_total=100000, product="Third Product"),
        ])
        lines = self.env['lyd.sale.record'].search([], order='id desc', limit=1).line_ids.sorted('id')
        self.assertEqual(lines.mapped('price_unit'), [55000, 35000, 50000])
        self.assertEqual(lines.mapped('price_unit_adjusted'), [True, True, False])
        self.assertIn("Unit price adjusted in 2 lines", result['params']['message'])

    # ------------------------------------------------------------------
    # Access rights (N1)
    # ------------------------------------------------------------------

    def test_regular_user_can_import_and_create_related_records(self):
        """The importer has no right to create partners, products or users
        (N1): the wizard creates them itself."""
        self.assertFalse(self.user_importer.has_group('base.group_partner_manager'))
        self.assertFalse(self.user_importer.has_group('product.group_product_manager'))
        self.assertFalse(self.user_importer.has_group('base.group_erp_manager'))
        self._import([self._row(customer="Importer Customer", salesperson="Importer Salesperson", product="Importer Product")],
                     user=self.user_importer)
        sale = self.env['lyd.sale.record'].search([], order='id desc', limit=1)
        self.assertEqual(sale.partner_id.name, "Importer Customer")
        self.assertEqual(sale.user_id.name, "Importer Salesperson")
        self.assertEqual(sale.line_ids.product_id.name, "Importer Product")
        self.assertEqual(sale.create_uid, self.user_importer)

    def test_user_without_group_cannot_import(self):
        with self.assertRaises(AccessError):
            self._import([self._row()], user=self.user_no_access)

    def test_success_notification(self):
        result = self._import([self._row()])
        self.assertEqual(result['params']['next']['res_model'], 'lyd.sale.record')
        self.assertEqual(
            result['params']['message'],
            "1 sales with 1 lines imported. New customers: 0, salespeople: 0, products: 0. "
            "Unit price adjusted in 0 lines.",
        )
