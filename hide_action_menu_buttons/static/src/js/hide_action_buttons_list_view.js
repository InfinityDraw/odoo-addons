/** @odoo-module **/

import { patch} from "@web/core/utils/patch";
import {ListController} from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";

patch(ListController.prototype,  {
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

            if (result.models.includes(self.props.resModel) && result.group_hide_action_menu_button_view_list) {
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