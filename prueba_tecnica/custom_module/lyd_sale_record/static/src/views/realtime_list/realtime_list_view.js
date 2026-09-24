import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { RealtimeListController } from "@lyd_sale_record/views/realtime_list/realtime_list_controller";
import { RealtimeListRenderer } from "@lyd_sale_record/views/realtime_list/realtime_list_renderer";

export const realtimeListView = {
    ...listView,
    Controller: RealtimeListController,
    Renderer: RealtimeListRenderer,
};

registry.category("views").add("lyd_sale_record_realtime_list", realtimeListView);
