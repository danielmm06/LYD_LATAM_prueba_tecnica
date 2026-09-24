# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class LydSaleRecordLine(models.Model):
    _name = 'lyd.sale.record.line'
    _description = 'Sale Record Line'
    _order = 'order_id, id'

    order_id = fields.Many2one(
        'lyd.sale.record', string="Sale Record",
        required=True, ondelete='cascade', index=True, copy=False)
    company_id = fields.Many2one(related='order_id.company_id')
    currency_id = fields.Many2one(related='order_id.currency_id')
    product_id = fields.Many2one(
        'product.product', string="Product",
        required=True, index=True, ondelete='restrict', check_company=True)
    quantity = fields.Float(string="Quantity", digits='Product Unit', required=True)
    price_unit = fields.Float(
        string="Unit Price", min_display_digits='Product Price',
        required=True, aggregator='avg')
    price_total = fields.Monetary(string="Total Amount", required=True)
    price_unit_adjusted = fields.Boolean(string="Unit Price Adjusted", readonly=True)

    _quantity_positive = models.Constraint(
        'CHECK (quantity > 0)',
        "The quantity must be greater than zero.",
    )
    _price_total_positive = models.Constraint(
        'CHECK (price_total > 0)',
        "The total amount must be greater than zero.",
    )

    def _compute_display_name(self):
        for line in self:
            line.display_name = "%s (%s)" % (line.product_id.name, line.order_id.date)

    # Not triggered by price_unit: the onchange itself sets price_unit, and the onchange
    # engine re-runs the onchanges of the fields it modifies, which would reset the
    # adjusted flag to False right after adjusting the price. The server rule in
    # create/write still covers manual changes of the unit price.
    @api.onchange('quantity', 'price_total')
    def _onchange_price_amounts(self):
        for line in self:
            vals = {
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'price_total': line.price_total,
            }
            line._prepare_price_unit(vals, record=line)
            if 'price_unit' in vals:
                line.price_unit = vals['price_unit']
            if 'price_unit_adjusted' in vals:
                line.price_unit_adjusted = vals['price_unit_adjusted']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._prepare_price_unit(vals)
        return super().create(vals_list)

    def write(self, vals):
        if any(field_name in vals for field_name in ('quantity', 'price_unit', 'price_total')):
            for line in self:
                line_vals = dict(vals)
                line._prepare_price_unit(line_vals, record=line)
                super(LydSaleRecordLine, line).write(line_vals)
            return True
        return super().write(vals)

    def _prepare_price_unit(self, vals, record=None):
        """Enforce that ``price_unit`` is always consistent with ``quantity`` and
        ``price_total`` (D4/N4).

        Adjusts ``vals['price_unit']`` in place, and sets ``vals['price_unit_adjusted']``,
        when the final quantity, unit price and total amount do not match, or when no
        unit price is provided at all. ``vals`` may be a partial ``write`` payload, in
        which case the missing values are read from ``record``.
        """
        quantity = vals['quantity'] if 'quantity' in vals else (record.quantity if record else 0.0)
        price_total = vals['price_total'] if 'price_total' in vals else (record.price_total if record else 0.0)
        price_unit = vals['price_unit'] if 'price_unit' in vals else (record.price_unit if record else 0.0)
        if not quantity:
            return
        if 'order_id' in vals:
            currency = self.env['lyd.sale.record'].browse(vals['order_id']).company_id.currency_id
        elif record:
            currency = record.order_id.company_id.currency_id
        else:
            currency = self.env.company.currency_id
        if not price_unit or currency.compare_amounts(quantity * price_unit, price_total) != 0:
            vals['price_unit'] = price_total / quantity
            vals['price_unit_adjusted'] = True
        else:
            vals['price_unit_adjusted'] = False
