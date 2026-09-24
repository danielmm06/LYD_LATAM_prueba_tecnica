# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import date_utils

SALE_RECORD_STATE = [
    ('draft', "Draft"),
    ('confirmed', "Confirmed"),
    ('cancelled', "Cancelled"),
]


class LydSaleRecord(models.Model):
    _name = 'lyd.sale.record'
    _description = 'Sale Record'
    _order = 'date desc, id desc'

    date = fields.Date(required=True, index=True)
    partner_id = fields.Many2one(
        'res.partner', string="Customer",
        required=True, index=True, ondelete='restrict', check_company=True)
    user_id = fields.Many2one(
        'res.users', string="Salesperson",
        required=True, index=True, ondelete='restrict',
        domain=[('share', '=', False)])
    state = fields.Selection(
        SALE_RECORD_STATE,
        required=True, index=True, default='draft')
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    import_file_name = fields.Char(string="Import File", readonly=True)
    line_ids = fields.One2many('lyd.sale.record.line', 'order_id', string="Lines", copy=True)
    amount_total = fields.Monetary(
        string="Total",
        compute='_compute_amount_total',
        store=True
    )

    @api.depends('line_ids.price_total')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.line_ids.mapped('price_total'))

    def _compute_display_name(self):
        for record in self:
            record.display_name = "%s (%s)" % (record.partner_id.name, record.date)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.ref('lyd_sale_record.lyd_sale_record_group_user')._bus_send(
            'lyd.sale.record/created', {'count': len(records)},
        )
        return records

    @api.model
    @api.readonly
    def get_dashboard_data(self, domain):
        """Return the KPI figures for the current month and for the given search domain."""
        today = fields.Date.context_today(self)
        month_domain = [
            ('date', '>=', date_utils.start_of(today, 'month')),
            ('date', '<=', date_utils.end_of(today, 'month')),
        ]
        month_total, month_count = self._get_total_and_count(month_domain)
        filter_total, filter_count = self._get_total_and_count(domain)
        return {
            'currency_id': self.env.company.currency_id.id,
            'month_total': month_total,
            'month_count': month_count,
            'filter_total': filter_total,
            'filter_count': filter_count,
        }

    def _get_total_and_count(self, domain):
        [(total, count)] = self._read_group(domain, [], ['amount_total:sum', '__count'])
        return total, count
