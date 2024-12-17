/** @odoo-module **/
import {Component, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";

export class GocardlessDialog extends Component {
    setup() {
        this.state = useState({
            searchString: "",
            country: false,
            institutions: this.props.context.institutions,
        });
    }
    onChangeCountry(event) {
        var country = false;
        if (
            event.target.selectedOptions.length &&
            event.target.selectedOptions[0].attributes.length
        ) {
            country = event.target.selectedOptions[0].value;
        }
        this.state.country = country;
        this.state.institutions = this.get_institutions(
            country,
            this.state.searchString
        );
    }
    onInstitutionSearch(event) {
        var searchString = event.target.value;
        this.state.searchString = searchString;
        this.state.institutions = this.get_institutions(
            this.state.country,
            searchString
        );
    }
    get_institutions(country, searchString) {
        var institutions = this.props.context.institutions;
        if (country) {
            institutions.filter((institution) =>
                institution.countries.includes(country)
            );
        }
        return institutions.filter((institution) =>
            institution.name.toUpperCase().includes(searchString.toUpperCase())
        );
    }

    get country_names() {
        return this.props.context.country_names;
    }
}
GocardlessDialog.template =
    "account_statement_import_online_gocardless.OnlineSyncSearchBankGoCardless";
GocardlessDialog.components = {Dialog};

async function OnlineSyncAccountInstitutionSelector(env, action) {
    env.services.dialog.add(GocardlessDialog, {
        title: _t("Gocardless selection"),
        context: action.context,
        onClickInstitution: async function (institutionId) {
            if (!institutionId) {
                return;
            }
            await env.services.orm.write(
                "online.bank.statement.provider",
                [action.context.provider_id],
                {gocardless_institution_id: institutionId}
            );
            var redirect_url = await env.services.orm.call(
                "online.bank.statement.provider",
                "action_check_gocardless_agreement",
                [[action.context.provider_id]]
            );
            if (redirect_url !== undefined) {
                window.location.replace(redirect_url);
            }
        },
    });
}

registry
    .category("actions")
    .add(
        "online_sync_institution_selector_gocardless",
        OnlineSyncAccountInstitutionSelector
    );
