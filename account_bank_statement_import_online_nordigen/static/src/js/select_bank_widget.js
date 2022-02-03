odoo.define(
    "account_bank_statement_import_online_nordigen.acc_config_widget_nordigen",
    function(require) {
        "use strict";

        require("web.dom_ready");
        var core = require("web.core");
        var AbstractAction = require("web.AbstractAction");
        var QWeb = core.qweb;
        var framework = require("web.framework");

        var OnlineSyncAccountInstitutionSelector = AbstractAction.extend({
            template: "OnlineSyncSearchBankNordigen",
            init: function(parent, action, options) {
                this._super(parent, action, options);
                this.context = action.context;
                this.results = action.context.institutions;
                this.country_names = action.context.country_names;
                this.country_selected = action.context.country;
            },

            start: function() {
                const self = this;
                const $selectCountries = this.$el.find(".country_select");
                const $countryOptions = $(
                    QWeb.render("OnlineSyncSearchBankNordigenCountries", {
                        country_names: this.country_names,
                    })
                );
                $countryOptions.appendTo($selectCountries);
                if (
                    $selectCountries.find("option[value=" + this.country_selected + "]")
                        .length !== 0
                ) {
                    $selectCountries.val(this.country_selected);
                    $selectCountries.change();
                }
                $selectCountries.change(function() {
                    self.country_selected = this.selectedOptions[0].value;
                    return self.renderSearchResult();
                });
                this.displayState();
                self.$el.find("#bank_search_input").on("keyup", function() {
                    const input = $(".institution-search-input");
                    const filter = input[0].value.toUpperCase();
                    const institutionList = $(".list-institution");

                    for (let i = 0; i < institutionList.length; i++) {
                        const txtValue = institutionList[i].textContent;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            institutionList[i].style.display = "";
                        } else {
                            institutionList[i].style.display = "none";
                        }
                    }
                });
            },

            displayState: function() {
                if (this.results.length > 0) {
                    this.renderSearchResult();
                }
            },

            renderElement: function() {
                this._super.apply(this, arguments);
            },

            renderSearchResult: function() {
                var self = this;
                this.$(".institution-container").html("");
                const filteredInstitutions = this.results.filter(function(institution) {
                    return institution.countries.includes(self.country_selected);
                });
                var $searchResults = $(
                    QWeb.render("OnlineSyncSearchBankNordigenList", {
                        institutions: filteredInstitutions,
                    })
                );
                $searchResults.find("a").click(function() {
                    framework.blockUI();
                    const id = this.getAttribute("data-institution");
                    if (id) {
                        return self
                            ._rpc({
                                model: "account.journal",
                                method: "write",
                                args: [
                                    [self.context.journal_id],
                                    {nordigen_institution_id: id},
                                ],
                            })
                            .then(function() {
                                return self
                                    ._rpc({
                                        model: "online.bank.statement.provider",
                                        method: "action_check_agreement",
                                        args: [self.context.active_ids],
                                    })
                                    .then(function(redirect_url) {
                                        window.location.replace(redirect_url);
                                    });
                            });
                    }
                });
                $searchResults.appendTo(self.$(".institution-container"));
            },
        });
        core.action_registry.add(
            "online_sync_institution_selector_nordigen",
            OnlineSyncAccountInstitutionSelector
        );
        return {
            OnlineSyncAccountInstitutionSelector: OnlineSyncAccountInstitutionSelector,
        };
    }
);
