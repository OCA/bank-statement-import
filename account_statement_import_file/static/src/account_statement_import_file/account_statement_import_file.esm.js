/** @odoo-module **/

import {DashboardKanbanView} from "@account/components/bills_upload/bills_upload";

export class DashboardKanbanController extends DashboardKanbanView.Controller {
    async uploadStatement() {
        console.log(this);
        return this.actionService.doAction(
            "account_statement_import_file.account_statement_import_action"
        );
    }
}

DashboardKanbanView.Controller = DashboardKanbanController;
DashboardKanbanView.buttonTemplate =
    "account_statement_import_file.DashboardKanbanView.Buttons";
