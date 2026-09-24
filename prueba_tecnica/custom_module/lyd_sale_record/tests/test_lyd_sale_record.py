# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from .common import LydSaleRecordCommon


@tagged('post_install', '-at_install')
class TestLydSaleRecord(LydSaleRecordCommon):

    # ------------------------------------------------------------------
    # Master-detail structure
    # ------------------------------------------------------------------

    def test_header_and_lines(self):
        sale = self.env['lyd.sale.record'].create(self._sale_vals(lines=[
            {'quantity': 2, 'price_unit': 50000, 'price_total': 100000},
            {'quantity': 1, 'price_unit': 30000, 'price_total': 30000},
        ]))
        self.assertEqual(len(sale.line_ids), 2)
        self.assertEqual(sale.line_ids.order_id, sale)
        self.assertEqual(sale.amount_total, 130000)
        self.assertEqual(sale.currency_id, self.currency)
        self.assertEqual(sale.line_ids.currency_id, self.currency)
        self.assertEqual(sale.line_ids.company_id, self.env.company)
        self.assertEqual(sale.display_name, "Existing Customer (2026-06-01)")

    def test_amount_total_is_recomputed(self):
        sale = self.env['lyd.sale.record'].create(self._sale_vals(lines=[
            {'quantity': 2, 'price_unit': 50000, 'price_total': 100000},
            {'quantity': 1, 'price_unit': 30000, 'price_total': 30000},
        ]))
        sale.line_ids[0].price_total = 120000
        self.assertEqual(sale.amount_total, 150000)
        sale.line_ids[1].unlink()
        self.assertEqual(sale.amount_total, 120000)
        sale.write({'line_ids': [Command.create({'product_id': self.product.id, 'quantity': 1, 'price_total': 5000})]})
        self.assertEqual(sale.amount_total, 125000)

    def test_lines_are_deleted_with_their_sale(self):
        sale = self.env['lyd.sale.record'].create(self._sale_vals())
        lines = sale.line_ids
        sale.unlink()
        self.assertFalse(lines.exists())

    def test_related_records_cannot_be_deleted_while_used(self):
        self.env['lyd.sale.record'].create(self._sale_vals())
        for record in (self.product, self.partner):
            with self.subTest(model=record._name), mute_logger('odoo.sql_db'), self.assertRaises(Exception), self.env.cr.savepoint():
                record.unlink()
                self.env.flush_all()

    # ------------------------------------------------------------------
    # SQL constraints (moved to the line)
    # ------------------------------------------------------------------

    def test_line_quantity_must_be_positive(self):
        for quantity in (0, -1):
            with self.subTest(quantity=quantity), mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.env.cr.savepoint():
                self.env['lyd.sale.record'].create(self._sale_vals(lines=[
                    {'quantity': quantity, 'price_unit': 1000, 'price_total': 1000},
                ]))
                self.env.flush_all()

    def test_line_total_must_be_positive(self):
        for price_total in (0, -1000):
            with self.subTest(price_total=price_total), mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.env.cr.savepoint():
                self.env['lyd.sale.record'].create(self._sale_vals(lines=[
                    {'quantity': 1, 'price_unit': 1000, 'price_total': price_total},
                ]))
                self.env.flush_all()

    def test_constraints_live_on_the_line_table(self):
        self.env.cr.execute("""
            SELECT conrelid::regclass::text, conname
              FROM pg_constraint
             WHERE contype = 'c' AND conname LIKE 'lyd_sale_record%%positive'
        """)
        constraints = set(self.env.cr.fetchall())
        self.assertEqual(constraints, {
            ('lyd_sale_record_line', 'lyd_sale_record_line_quantity_positive'),
            ('lyd_sale_record_line', 'lyd_sale_record_line_price_total_positive'),
        })

    # ------------------------------------------------------------------
    # Unit price adjustment (D4 / N3 / N4)
    # ------------------------------------------------------------------

    def _line(self, **values):
        return self.env['lyd.sale.record'].create(self._sale_vals(lines=[values])).line_ids

    def test_consistent_unit_price_is_kept(self):
        line = self._line(quantity=2, price_unit=50000, price_total=100000)
        self.assertEqual(line.price_unit, 50000)
        self.assertFalse(line.price_unit_adjusted)

    def test_inconsistent_unit_price_is_adjusted(self):
        line = self._line(quantity=2, price_unit=50000, price_total=110000)
        self.assertEqual(line.price_unit, 55000)
        self.assertTrue(line.price_unit_adjusted)

    def test_missing_unit_price_is_computed(self):
        line = self._line(quantity=3, price_total=105000)
        self.assertEqual(line.price_unit, 35000)
        self.assertTrue(line.price_unit_adjusted)

    def test_non_exact_division_is_stored_without_truncation(self):
        line = self._line(quantity=3, price_unit=30000, price_total=100000)
        self.assertAlmostEqual(line.price_unit, 100000 / 3, places=6)
        self.assertTrue(line.price_unit_adjusted)

    def test_rounding_difference_below_currency_precision_is_not_adjusted(self):
        # 3 x 33333.33 = 99999.99 -> consistent with a total of 99999.99
        line = self._line(quantity=3, price_unit=33333.33, price_total=99999.99)
        self.assertEqual(line.price_unit, 33333.33)
        self.assertFalse(line.price_unit_adjusted)

    def test_write_readjusts_the_unit_price(self):
        line = self._line(quantity=2, price_unit=50000, price_total=100000)
        line.quantity = 4
        self.assertEqual(line.price_unit, 25000)
        self.assertTrue(line.price_unit_adjusted)
        line.write({'quantity': 5, 'price_unit': 20000})
        self.assertEqual(line.price_unit, 20000)
        self.assertFalse(line.price_unit_adjusted)
        line.price_total = 150000
        self.assertEqual(line.price_unit, 30000)
        self.assertTrue(line.price_unit_adjusted)

    def test_form_onchange_adjusts_the_unit_price(self):
        """Uses the real form view (editable list of lines) and its onchange."""
        with Form(self.env['lyd.sale.record']) as sale_form:
            sale_form.partner_id = self.partner
            sale_form.user_id = self.salesperson
            sale_form.date = date(2026, 6, 1)
            with sale_form.line_ids.new() as line_form:
                line_form.product_id = self.product
                line_form.quantity = 2
                line_form.price_total = 110000
                self.assertEqual(line_form.price_unit, 55000)
                self.assertTrue(line_form.price_unit_adjusted)
        sale = sale_form.save()
        self.assertEqual(sale.state, 'draft')
        self.assertEqual(sale.line_ids.price_unit, 55000)
        self.assertTrue(sale.line_ids.price_unit_adjusted)  # the flag is saved too
        self.assertEqual(sale.amount_total, 110000)
        # editing the quantity of a consistent line re-adjusts the unit price
        with Form(sale) as sale_form:
            with sale_form.line_ids.edit(0) as line_form:
                line_form.price_total = 100000
                line_form.quantity = 4
                self.assertEqual(line_form.price_unit, 25000)
                self.assertTrue(line_form.price_unit_adjusted)
        self.assertEqual(sale.line_ids.price_unit, 25000)
        self.assertTrue(sale.line_ids.price_unit_adjusted)

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------

    def test_access_rights(self):
        sale = self.env['lyd.sale.record'].create(self._sale_vals())
        # user: read / write / create, cannot delete a sale but can remove its lines
        sale_as_user = sale.with_user(self.user_importer)
        sale_as_user.read(['amount_total'])
        sale_as_user.write({'state': 'draft'})
        with self.assertRaises(AccessError):
            sale_as_user.unlink()
        sale_as_user.line_ids.unlink()
        # manager: can delete
        sale.with_user(self.user_manager).unlink()
        # no group: no access at all
        with self.assertRaises(AccessError):
            self.env['lyd.sale.record'].with_user(self.user_no_access).search([])
        with self.assertRaises(AccessError):
            self.env['lyd.sale.record.import'].with_user(self.user_no_access).create({})

    def test_multi_company_rule(self):
        company_2 = self.env['res.company'].create({'name': "LYD Company 2"})
        sale_company_2 = self.env['lyd.sale.record'].create(self._sale_vals(company_id=company_2.id))
        sale_company_1 = self.env['lyd.sale.record'].create(self._sale_vals())
        Sales = self.env['lyd.sale.record'].with_user(self.user_manager)
        visible = Sales.search([('id', 'in', (sale_company_1 | sale_company_2).ids)])
        self.assertEqual(visible, sale_company_1)
        lines = self.env['lyd.sale.record.line'].with_user(self.user_manager).search(
            [('order_id', 'in', (sale_company_1 | sale_company_2).ids)])
        self.assertEqual(lines, sale_company_1.line_ids)

    # ------------------------------------------------------------------
    # Dashboard KPIs
    # ------------------------------------------------------------------

    @freeze_time('2026-09-15')
    def test_dashboard_data(self):
        Sales = self.env['lyd.sale.record']
        Sales.search([]).unlink()
        Sales.create([
            self._sale_vals(date=date(2026, 9, 1), lines=[
                {'quantity': 1, 'price_total': 1000},
                {'quantity': 1, 'price_total': 500},
            ]),
            self._sale_vals(date=date(2026, 9, 30), lines=[{'quantity': 1, 'price_total': 2000}]),
            self._sale_vals(date=date(2026, 8, 31), lines=[{'quantity': 1, 'price_total': 4000}]),
            self._sale_vals(date=date(2026, 10, 1), state='draft', lines=[{'quantity': 1, 'price_total': 8000}]),
        ])
        data = Sales.get_dashboard_data([])
        self.assertEqual(data['month_total'], 3500)
        self.assertEqual(data['month_count'], 2)  # sales (headers), not lines
        self.assertEqual(data['filter_total'], 15500)
        self.assertEqual(data['filter_count'], 4)
        self.assertEqual(data['currency_id'], self.currency.id)
        filtered = Sales.get_dashboard_data([('state', '=', 'draft')])
        self.assertEqual((filtered['filter_total'], filtered['filter_count']), (8000, 1))
