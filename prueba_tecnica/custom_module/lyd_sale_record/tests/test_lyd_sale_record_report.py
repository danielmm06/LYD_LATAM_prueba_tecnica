# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import sql

from .common import LydSaleRecordCommon


@tagged('post_install', '-at_install')
class TestLydSaleRecordReport(LydSaleRecordCommon):

    def test_report_is_a_postgresql_view(self):
        Report = self.env['lyd.sale.record.report']
        self.assertFalse(Report._auto)
        self.assertEqual(sql.table_kind(self.env.cr, Report._table), sql.TableKind.View)

    def test_one_row_per_line_with_header_values(self):
        sale = self.env['lyd.sale.record'].create(self._sale_vals(date=date(2026, 6, 3), state='draft', lines=[
            {'quantity': 2, 'price_unit': 50000, 'price_total': 110000},
            {'quantity': 1, 'price_unit': 30000, 'price_total': 30000},
        ]))
        rows = self.env['lyd.sale.record.report'].search([('order_id', '=', sale.id)])
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows.ids), set(sale.line_ids.ids))
        for row in rows:
            line = sale.line_ids.browse(row.id)
            self.assertEqual(
                (row.date, row.partner_id, row.user_id, row.state, row.company_id, row.currency_id),
                (sale.date, sale.partner_id, sale.user_id, sale.state, sale.company_id, sale.currency_id),
            )
            self.assertEqual(
                (row.product_id, row.quantity, row.price_unit, row.price_total, row.price_unit_adjusted),
                (line.product_id, line.quantity, line.price_unit, line.price_total, line.price_unit_adjusted),
            )
        self.assertEqual(sum(rows.mapped('price_total')), sale.amount_total)

    def test_report_reflects_pending_changes(self):
        """``_depends`` makes the ORM flush the source models before reading the view."""
        sale = self.env['lyd.sale.record'].create(self._sale_vals())
        sale.state = 'cancelled'
        sale.line_ids.price_total = 200000
        row = self.env['lyd.sale.record.report'].search([('order_id', '=', sale.id)])
        self.assertEqual(row.state, 'cancelled')
        self.assertEqual(row.price_total, 200000)

    def test_grouping_by_product_and_salesperson(self):
        other_product = self.env['product.product'].create({'name': "Other Product"})
        sale = self.env['lyd.sale.record'].create(self._sale_vals(lines=[
            {'quantity': 1, 'price_total': 1000},
            {'quantity': 1, 'price_total': 2000, 'product_id': other_product.id},
            {'quantity': 1, 'price_total': 4000},
        ]))
        groups = dict(self.env['lyd.sale.record.report']._read_group(
            [('order_id', '=', sale.id)], ['product_id'], ['price_total:sum']))
        self.assertEqual(groups, {self.product: 5000, other_product: 2000})
        [(salesperson, total)] = self.env['lyd.sale.record.report']._read_group(
            [('order_id', '=', sale.id)], ['user_id'], ['price_total:sum'])
        self.assertEqual((salesperson, total), (self.salesperson, 7000))

    def test_report_is_read_only(self):
        sale = self.env['lyd.sale.record'].create(self._sale_vals())
        Report = self.env['lyd.sale.record.report'].with_user(self.user_importer)
        row = Report.search([('order_id', '=', sale.id)])
        self.assertEqual(len(row), 1)
        with self.assertRaises(AccessError):
            row.write({'quantity': 10})
        with self.assertRaises(AccessError):
            self.env['lyd.sale.record.report'].with_user(self.user_no_access).search([])
