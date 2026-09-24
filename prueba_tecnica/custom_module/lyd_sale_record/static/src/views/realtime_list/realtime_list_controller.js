import { onWillUnmount, status } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

// Leading + trailing throttle interval for bus-triggered list reloads (D10/section 8).
const RELOAD_THROTTLE_INTERVAL = 2000;

export class RealtimeListController extends ListController {
    setup() {
        super.setup();
        this.busService = useService("bus_service");

        this.reloadTimer = null;
        this.reloadPending = false;
        this.isReloading = false;
        this.lastReloadTime = 0;

        this.onRecordsCreated = this.onRecordsCreated.bind(this);
        this.flushReload = this.flushReload.bind(this);
        this.busService.subscribe("lyd.sale.record/created", this.onRecordsCreated);

        onWillUnmount(() => {
            this.busService.unsubscribe("lyd.sale.record/created", this.onRecordsCreated);
            browser.clearTimeout(this.reloadTimer);
            this.reloadTimer = null;
            this.reloadPending = false;
        });
    }

    /**
     * Bus callback (fixed reference, bound in setup): schedules a reload without
     * reacting once per event. The timer's absence means we are in a calm period,
     * so a new one fires immediately (leading edge); otherwise the event is
     * absorbed by the timer already scheduled (trailing edge).
     */
    onRecordsCreated() {
        if (status(this) === "destroyed") {
            return;
        }
        this.reloadPending = true;
        if (this.reloadTimer) {
            return;
        }
        const wait = Math.max(0, this.lastReloadTime + RELOAD_THROTTLE_INTERVAL - Date.now());
        this.reloadTimer = browser.setTimeout(this.flushReload, wait);
    }

    async flushReload() {
        this.reloadTimer = null;
        if (status(this) === "destroyed" || !this.reloadPending) {
            return;
        }
        const root = this.model.root;
        if (this.isReloading || root.editedRecord || root.selection.length) {
            // Reloading now would discard in-progress edition or selection: retry later
            // locally, without making a new request, and without losing the pending event.
            this.reloadTimer = browser.setTimeout(this.flushReload, RELOAD_THROTTLE_INTERVAL);
            return;
        }
        this.reloadPending = false;
        this.lastReloadTime = Date.now();
        this.isReloading = true;
        try {
            await this.model.load();
        } finally {
            this.isReloading = false;
        }
    }
}
