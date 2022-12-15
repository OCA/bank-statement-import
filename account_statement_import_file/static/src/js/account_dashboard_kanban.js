odoo.define("account_statement_import_file.dashboard.kanban", function (require) {
    "use strict";

    var KanbanView = require("@web/views/kanban/kanban_view");
    var viewRegistry = require("@web/core/registry");

    var AccountDashboardView = viewRegistry.registry
        .category("views")
        .get("account_dashboard_kanban");
    if (AccountDashboardView !== undefined) {
        AccountDashboardView.buttonTemplate = "AccountDashboardView.buttons";
        Object.assign(KanbanView.kanbanView.Controller.prototype, {
            importOcaStatement: async function (ev) {
                ev.stopPropagation();
                return this.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: "account.statement.import",
                    views: [[false, "form"]],
                    target: "new",
                });
            },
        });
    }
});
