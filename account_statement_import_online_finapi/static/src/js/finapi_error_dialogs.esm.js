/** @odoo-module **/

import {WarningDialog} from "@web/core/errors/error_dialogs";
import {registry} from "@web/core/registry";

/**
 * Render finAPI errors as plain warnings instead of a raw RPC traceback.
 *
 * The web client picks its error dialog from the "error_dialogs" registry by
 * the *fully qualified* Python exception name (see rpcErrorHandler in
 * @web/core/errors/error_handlers). Only odoo.exceptions.* names are
 * registered by core, so an addon-defined subclass of UserError -- which our
 * finAPI exceptions are -- falls through to the generic RPCErrorDialog and
 * dumps a stack trace at the user. Registering the names restores the
 * intended UserError behaviour.
 *
 * Keep these strings in sync with models/finapi_interface.py; a test asserts
 * that they still match the real class paths.
 */
const errorDialogRegistry = registry.category("error_dialogs");

errorDialogRegistry.add(
    "odoo.addons.account_statement_import_online_finapi.models.finapi_interface.FinapiApiError",
    WarningDialog
);
errorDialogRegistry.add(
    "odoo.addons.account_statement_import_online_finapi.models.finapi_interface.FinapiAuthError",
    WarningDialog
);
errorDialogRegistry.add(
    "odoo.addons.account_statement_import_online_finapi.models.finapi_interface.FinapiWebFormRequiredError",
    WarningDialog
);
