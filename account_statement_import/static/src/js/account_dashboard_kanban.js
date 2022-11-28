odoo.define("account_statement_import.dashboard.kanban", function (require) {
    "use strict";
    var viewRegistry = require("web.view_registry");

    var AccountDashboardView = viewRegistry.get("account_dashboard_kanban");
    // Value can be undefined on some test scenarios. Avoid an error by checking if it is defined
    if (AccountDashboardView !== undefined) {
        var AccountDashboardController =
            AccountDashboardView.prototype.config.Controller;
        AccountDashboardController.include({
            buttons_template: "AccountDashboardView.buttons",
            // We are reusing the create button
            _onButtonNew: function (ev) {
                ev.stopPropagation();
                return this.trigger_up("do_action", {
                    action: "account_statement_import.account_statement_import_action",
                });
            },
        });
        return {
            AccountDashboardView: AccountDashboardView,
            AccountDashboardController: AccountDashboardController,
        };
    }
});
