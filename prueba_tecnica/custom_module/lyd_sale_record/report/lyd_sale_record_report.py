# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.sql import drop_view_if_exists, SQL

from odoo.addons.lyd_sale_record.models.lyd_sale_record import SALE_RECORD_STATE


class LydSaleRecordReport(models.Model):
    _name = 'lyd.sale.record.report'
    _description = 'Sales Analysis Report'
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    order_id = fields.Many2one('lyd.sale.record', string="Sale Record", readonly=True)
    date = fields.Date(string="Date", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    user_id = fields.Many2one('res.users', string="Salesperson", readonly=True)
    state = fields.Selection(SALE_RECORD_STATE, string="Status", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    product_id = fields.Many2one('product.product', string="Product", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=True)
    price_unit = fields.Float(string="Unit Price", readonly=True, aggregator='avg')
    price_total = fields.Monetary(string="Total Amount", readonly=True)
    price_unit_adjusted = fields.Boolean(string="Unit Price Adjusted", readonly=True)

    _depends = {
        'lyd.sale.record': ['date', 'partner_id', 'user_id', 'state', 'company_id'],
        'lyd.sale.record.line': ['order_id', 'product_id', 'quantity', 'price_unit', 'price_total', 'price_unit_adjusted'],
        'res.company': ['currency_id'],
    }

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("CREATE OR REPLACE VIEW %s AS (%s)", SQL.identifier(self._table), self._query()))

    def _query(self) -> SQL:
        return SQL(
            """
            SELECT
                l.id AS id,
                l.order_id AS order_id,
                o.date AS date,
                o.partner_id AS partner_id,
                o.user_id AS user_id,
                o.state AS state,
                o.company_id AS company_id,
                c.currency_id AS currency_id,
                l.product_id AS product_id,
                l.quantity AS quantity,
                l.price_unit AS price_unit,
                l.price_total AS price_total,
                l.price_unit_adjusted AS price_unit_adjusted
            FROM lyd_sale_record_line l
            JOIN lyd_sale_record o ON o.id = l.order_id
            JOIN res_company c ON c.id = o.company_id
            """
        )
