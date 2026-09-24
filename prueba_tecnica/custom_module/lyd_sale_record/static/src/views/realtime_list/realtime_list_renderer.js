import { ListRenderer } from "@web/views/list/list_renderer";
import { SaleRecordDashboard } from "@lyd_sale_record/views/sale_record_dashboard/sale_record_dashboard";

export class RealtimeListRenderer extends ListRenderer {
    static template = "lyd_sale_record.RealtimeListRenderer";
    static components = {
        ...ListRenderer.components,
        SaleRecordDashboard,
    };
}
