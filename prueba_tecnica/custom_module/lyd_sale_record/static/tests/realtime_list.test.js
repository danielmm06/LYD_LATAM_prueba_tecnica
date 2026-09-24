import { describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineModels,
    fields,
    models,
    MockServer,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { RealtimeListController } from "@lyd_sale_record/views/realtime_list/realtime_list_controller";

// Must match RELOAD_THROTTLE_INTERVAL in realtime_list_controller.js (D10).
const INTERVAL = 2000;
const NOTIFICATION_TYPE = "lyd.sale.record/created";

class LydSaleRecord extends models.Model {
    _name = "lyd.sale.record";

    date = fields.Date();
    amount_total = fields.Float();

    _records = [
        { id: 1, date: "2026-06-01", amount_total: 100000 },
        { id: 2, date: "2026-06-02", amount_total: 110000 },
    ];

    get_dashboard_data() {
        return {
            currency_id: false,
            month_total: 0,
            month_count: 0,
            filter_total: 210000,
            filter_count: 2,
        };
    }
}

// mail is installed (dependency of product): its services need the mail mock models.
defineMailModels();
defineModels([LydSaleRecord]);

describe.current.tags("desktop");

describe("lyd_sale_record realtime list", () => {
    let reloadCount = 0;

    /** Mounts the list with the module's js_class and counts the list reloads. */
    async function mountRealtimeList() {
        reloadCount = 0;
        onRpc("web_search_read", () => {
            reloadCount++;
            expect.step("reload");
        });
        const view = await mountView({
            type: "list",
            resModel: "lyd.sale.record",
            arch: `
                <list js_class="lyd_sale_record_realtime_list">
                    <field name="date"/>
                    <field name="amount_total"/>
                </list>`,
        });
        expect.verifySteps(["reload"]); // initial load
        return view;
    }

    /** Simulates the server notification sent by ``lyd.sale.record.create``. */
    async function notifyCreated() {
        MockServer.env["bus.bus"]._sendone("broadcast", NOTIFICATION_TYPE, { count: 1 });
        await animationFrame();
    }

    test("a single notification reloads the list immediately (leading edge)", async () => {
        await mountRealtimeList();
        await notifyCreated();
        await advanceTime(0);
        await animationFrame();
        expect.verifySteps(["reload"]);
        // nothing else is scheduled afterwards: no polling without events
        await advanceTime(INTERVAL * 5);
        await animationFrame();
        expect.verifySteps([]);
    });

    test("a short burst reloads at most twice (leading + trailing edge)", async () => {
        await mountRealtimeList();
        await notifyCreated(); // first event -> leading reload
        await advanceTime(0);
        await animationFrame();
        for (let i = 0; i < 20; i++) {
            await notifyCreated(); // absorbed by the open window
        }
        await advanceTime(0);
        await animationFrame();
        expect.verifySteps(["reload"]);
        await advanceTime(INTERVAL);
        await animationFrame();
        expect.verifySteps(["reload"]); // trailing reload: the last events are not lost
        await advanceTime(INTERVAL * 5);
        await animationFrame();
        expect.verifySteps([]);
    });

    test("a sustained stream keeps refreshing the list (no debounce starvation)", async () => {
        await mountRealtimeList();
        const initialLoads = reloadCount;
        // one event every 500 ms during 10 s: a debounce(2 s) would not reload until the end
        for (let elapsed = 0; elapsed < 10000; elapsed += 500) {
            await notifyCreated();
            await advanceTime(500);
            await animationFrame();
        }
        // the list was refreshed several times while the stream was still running
        const reloadsDuringStream = reloadCount - initialLoads;
        expect(reloadsDuringStream).toBeGreaterThan(3);
        // let the last window close: its trailing reload applies the last events
        await advanceTime(INTERVAL);
        await animationFrame();
        const reloads = reloadCount - initialLoads;
        // at most one reload per 2 s window over ~10 s (0, 2, 4, 6, 8, 10 s)
        expect(reloads).toBeLessThan(8);
        expect.verifySteps(Array(reloads).fill("reload"));
        await advanceTime(INTERVAL * 3);
        await animationFrame();
        expect.verifySteps([]); // stream over: nothing left scheduled
    });

    test("leaving the screen removes the listener and cancels the pending reload", async () => {
        // Spy on the controller itself: once destroyed, the ORM of a component never
        // sends requests anyway, so counting RPCs would not prove the cleanup.
        patchWithCleanup(RealtimeListController.prototype, {
            onRecordsCreated() {
                expect.step("event received");
                return super.onRecordsCreated(...arguments);
            },
            flushReload() {
                expect.step("flush");
                return super.flushReload(...arguments);
            },
        });
        const view = await mountRealtimeList();
        await notifyCreated();
        await advanceTime(0);
        await animationFrame();
        expect.verifySteps(["event received", "flush", "reload"]); // leading reload

        await notifyCreated(); // schedules a trailing flush...
        expect.verifySteps(["event received"]);
        view.__owl__.destroy(); // ...but the user leaves the screen before it fires
        await advanceTime(INTERVAL * 2);
        await animationFrame();
        expect.verifySteps([]); // the pending timer was cancelled: no flush

        await notifyCreated(); // event after leaving the screen
        await advanceTime(INTERVAL * 2);
        await animationFrame();
        expect.verifySteps([]); // nobody listens anymore: no orphan subscription
    });

    test("reload is deferred while records are selected, then applied", async () => {
        await mountRealtimeList();
        await contains(".o_data_row:first-child .o_list_record_selector input").click();
        await notifyCreated();
        await advanceTime(INTERVAL * 3);
        await animationFrame();
        expect.verifySteps([]); // the selection is not lost
        await contains(".o_data_row:first-child .o_list_record_selector input").click();
        await advanceTime(INTERVAL);
        await animationFrame();
        expect.verifySteps(["reload"]);
    });
});
