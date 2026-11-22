import {loadJS} from "@web/core/assets";
import {registry} from "@web/core/registry";

// Plaid requires Link to be loaded from its CDN, not bundled.
const PLAID_LINK_URL = "https://cdn.plaid.com/link/v2/stable/link-initialize.js";

export async function plaidLogin(env, action) {
    await loadJS(PLAID_LINK_URL);
    const {call_model, call_method, token, object_id} = action.params;
    const handler = window.Plaid.create({
        token,
        onSuccess: async (publicToken) => {
            const result = await env.services.orm.call(call_model, call_method, [
                publicToken,
                object_id,
            ]);
            await env.services.action.doAction(
                result || {type: "ir.actions.client", tag: "soft_reload"}
            );
        },
    });
    handler.open();
}

registry.category("actions").add("plaid_login", plaidLogin);
