# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
from datetime import date

from openpyxl import Workbook

from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user

HEADERS = [
    "Fecha", "Cliente", "Vendedor", "Producto",
    "Cantidad", "Valor Unitario", "Valor Total", "Estado",
]


class LydSaleRecordCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref('lyd_sale_record.lyd_sale_record_group_user')
        cls.group_manager = cls.env.ref('lyd_sale_record.lyd_sale_record_group_manager')
        cls.user_importer = new_test_user(
            cls.env, login='lyd_importer', name="LYD Importer",
            groups='base.group_user,lyd_sale_record.lyd_sale_record_group_user',
        )
        cls.user_manager = new_test_user(
            cls.env, login='lyd_manager', name="LYD Manager",
            groups='base.group_user,lyd_sale_record.lyd_sale_record_group_manager',
        )
        cls.user_no_access = new_test_user(
            cls.env, login='lyd_no_access', name="LYD No Access", groups='base.group_user',
        )
        cls.partner = cls.env['res.partner'].create({'name': "Existing Customer"})
        cls.salesperson = new_test_user(
            cls.env, login='existing.salesperson', name="Existing Salesperson",
        )
        cls.product = cls.env['product.product'].create({'name': "Existing Product"})
        cls.currency = cls.env.company.currency_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sale_vals(self, lines=None, **values):
        """Values of a sale record with its lines (``lines``: list of line dicts)."""
        lines = lines if lines is not None else [{'quantity': 2, 'price_unit': 50000, 'price_total': 100000}]
        return {
            'date': date(2026, 6, 1),
            'partner_id': self.partner.id,
            'user_id': self.salesperson.id,
            'state': 'confirmed',
            **values,
            'line_ids': [Command.create({'product_id': self.product.id, **line}) for line in lines],
        }

    def _xlsx(self, rows, headers=HEADERS):
        """Build an in-memory .xlsx file and return it base64-encoded, as a Binary field."""
        workbook = Workbook()
        sheet = workbook.active
        if headers is not None:
            sheet.append(headers)
        for row in rows:
            sheet.append(row)
        buffer = io.BytesIO()
        workbook.save(buffer)
        return base64.b64encode(buffer.getvalue())

    def _row(self, **overrides):
        """A valid Excel row; ``overrides`` replaces cells by header key."""
        row = {
            'date': date(2026, 6, 1),
            'customer': "Existing Customer",
            'salesperson': "Existing Salesperson",
            'product': "Existing Product",
            'quantity': 2,
            'price_unit': 50000,
            'price_total': 100000,
            'state': "Confirmada",
        }
        row.update(overrides)
        return list(row.values())

    def _wizard(self, rows=None, file_content=None, file_name='sales.xlsx', user=None, lang='en_US', headers=HEADERS):
        env = self.env(user=user) if user else self.env
        Wizard = env['lyd.sale.record.import'].with_context(lang=lang)
        return Wizard.create({
            'file': file_content if file_content is not None else self._xlsx(rows or [], headers=headers),
            'file_name': file_name,
        })

    def _import(self, rows=None, **kwargs):
        return self._wizard(rows, **kwargs).action_import()
