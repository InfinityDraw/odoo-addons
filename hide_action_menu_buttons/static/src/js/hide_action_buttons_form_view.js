/** @odoo-module **/
import { jsonrpc } from "@web/core/network/rpc_service";

import { patch} from "@web/core/utils/patch";
import { FormController } from '@web/views/form/form_controller';
import { useService } from "@web/core/utils/hooks";
patch(FormController.prototype,  {
    /**
     * @override
     */

    setup() {

        super.setup();
                this.rpc = useService("rpc");
        this.isMenu = true
        self = this;
        var domain = [];
        var fields = [];
          jsonrpc('/web/dataset/call_kw/hide.action.buttons/check_if_group_view',{
            model: 'hide.action.buttons',
            method: 'check_if_group_view',
            args: [domain, fields],
            kwargs: {},
        }).then(function(result) {


            if (result.models.includes(self.props.resModel) && result.group_hide_action_menu_button_view_form) {
                self.isMenu = false
            };
        })
    },


 get actionMenuItems() {
        const actionMenus = super.actionMenuItems;

        if (
            this.props.resModel === "stock.quant" &&
            (!this.props.context.inventory_mode || this.props.context.inventory_report_mode)
        ) {
            // hack so we don't show some of the default actions when it's inappropriate to
            const { print, action } = actionMenus;
            return {
                action: action.filter((a) => a.name !== _t("Set")),
                print: print.filter((a) => a.name !== _t("Count Sheet")),
            };
        }
             if (!self.isMenu) {
            delete actionMenus.action
        }
        return actionMenus;
    }


});