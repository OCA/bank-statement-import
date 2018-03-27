odoo.define('lr_account.ReconciliationRenderer', function (require) {
    "use strict";

    var LineRenderer = require('account.ReconciliationRenderer').LineRenderer;

    LineRenderer.include({
        // Set placeholder in partner_id field from communication_partner_name
        // in bank statement line
        start: function() {
            var def = this._super.apply(this, arguments);
            var self = this;
            return $.when(def).then(function() {
                var line = self._initialState.st_line;
                if (self.fields.partner_id && line.communication_partner_name) {
                    self.fields.partner_id.$el.find('input').attr('placeholder', line.communication_partner_name);
                }
            });
        }
    });

});