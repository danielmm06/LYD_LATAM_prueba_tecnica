# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.web.tests.test_js import unit_test_error_checker


@tagged('post_install', '-at_install')
class TestLydSaleRecordJs(HttpCase):
    """Runs the HOOT unit tests of the real-time list (throttle + cleanup)."""

    def test_realtime_list_unit_tests(self):
        self.browser_js(
            "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&filter=lyd_sale_record",
            "",
            "",
            login='admin',
            timeout=1800,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )
