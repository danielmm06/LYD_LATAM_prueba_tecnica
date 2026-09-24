import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";

export class SaleRecordDashboard extends Component {
    static template = "lyd_sale_record.SaleRecordDashboard";
    static props = { list: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.dashboardData = null;

        onWillStart(async () => {
            await this.updateDashboardData(this.props.list);
        });
        onWillUpdateProps(async (nextProps) => {
            await this.updateDashboardData(nextProps.list);
        });
    }

    async updateDashboardData(list) {
        this.dashboardData = await this.orm.call(
            "lyd.sale.record",
            "get_dashboard_data",
            [list ? list.domain : []],
        );
    }

    formatMonetary(value) {
        return formatMonetary(value || 0, { currencyId: this.dashboardData?.currency_id });
    }
}
