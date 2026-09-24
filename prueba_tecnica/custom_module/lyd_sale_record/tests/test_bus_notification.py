# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.bus.models.bus import channel_with_db, json_dump

from .common import LydSaleRecordCommon

NOTIFICATION_TYPE = 'lyd.sale.record/created'


@tagged('post_install', '-at_install')
class TestLydSaleRecordBusNotification(LydSaleRecordCommon):
    """The server notifies the real-time list once per batch of new sales (M5)."""

    def setUp(self):
        super().setUp()
        self.env.cr.precommit.run()  # flush notifications queued by the test setup
        self.last_bus_id = self.env['bus.bus'].sudo().search([], order='id desc', limit=1).id or 0

    def _sent_notifications(self):
        """Notifications of our type written since setUp (they are inserted on precommit)."""
        self.env.cr.precommit.run()
        messages = self.env['bus.bus'].sudo().search([('id', '>', self.last_bus_id)], order='id')
        return [
            (message.channel, json.loads(message.message))
            for message in messages
            if json.loads(message.message)['type'] == NOTIFICATION_TYPE
        ]

    def test_one_notification_per_create_batch(self):
        self.env['lyd.sale.record'].create([self._sale_vals() for _i in range(3)])
        notifications = self._sent_notifications()
        self.assertEqual(len(notifications), 1)
        channel, message = notifications[0]
        # sent to the module user group: only users with access receive it
        self.assertEqual(channel, json_dump(channel_with_db(self.env.cr.dbname, self.group_user)))
        self.assertEqual(message['payload'], {'count': 3})

    def test_one_notification_per_import(self):
        self._wizard([
            self._row(),
            self._row(customer="Second Customer"),
            self._row(customer="Third Customer"),
        ]).action_import()
        notifications = self._sent_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0][1]['payload'], {'count': 3})

    def test_no_notification_when_import_fails(self):
        wizard = self._wizard([self._row(), self._row(quantity=0)])
        with self.assertRaises(UserError):
            wizard.action_import()
        self.assertEqual(self._sent_notifications(), [])

    def test_editing_a_sale_does_not_notify(self):
        sale = self.env['lyd.sale.record'].create(self._sale_vals())
        self._sent_notifications()
        self.last_bus_id = self.env['bus.bus'].sudo().search([], order='id desc', limit=1).id
        sale.write({
            'state': 'cancelled',
            'line_ids': [Command.create({'product_id': self.product.id, 'quantity': 1, 'price_total': 1000})],
        })
        self.env['lyd.sale.record.line'].create({
            'order_id': sale.id, 'product_id': self.product.id, 'quantity': 1, 'price_total': 500,
        })
        self.assertEqual(self._sent_notifications(), [])
