/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { SaleOrderPopup } from "@ifdw_pos_sales_order_create_modify/js/SaleOrderPopup";


patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        this.dialog =  useService("dialog");
        this.notification = useService("notification");
        this.create_sale_order= this.pos.config.create_sale_order;
        this.update_sale_order=this.pos.config.update_sale_order;
    },

    async CheckOrderPartner(order) {
         if (!order.get_partner()) {
            this.notification.add(_t("Required set customer for create sale order"), 3000);
            let partner = await makeAwaitable(this.dialog, PartnerList);
            if (!partner) {
                return;
            }
            order.set_partner(partner);
        }
    },

    async OnCreateSaleOrderPopup() {
        let order = this.pos.get_order();
        if (order.get_total_with_tax() <= 0 || order.lines.length == 0) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Your shopping cart is empty !'),
            })
        }
        await this.CheckOrderPartner(order);
        await this.dialog.add(SaleOrderPopup, {
            order: order,
            pricelists: this.getPricelistList(),
            order_state: 'create',
            sale_order_auto_confirm: this.pos.config.sale_order_auto_confirm,
            sale_order_auto_delivery: this.pos.config.sale_order_auto_delivery,
            sale_order_auto_invoice: this.pos.config.sale_order_auto_invoice,
        });
    },

    async OnUpdateSaleOrderPopup() {
        let order = this.pos.get_order();
        if (order.get_total_with_tax() <= 0 || order.lines.length == 0) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Your shopping cart is empty !'),
            })
        }
        await this.CheckOrderPartner(order);

        const order_sale_id = order.get_orderlines().find((line) => line.sale_order_origin_id)?.sale_order_origin_id;
        if (order_sale_id){
            const sale_selected = await this.pos._getSaleOrder(order_sale_id.id);
            if (['draft', 'sent'].indexOf(sale_selected.state) == -1) {
                return this.dialog.add(ConfirmationDialog, {
                    title: _t("Warning"),
                    body: _t("Sale Order state is not Quotation or Quotation sent"),
                })
            } else {
                await this.dialog.add(SaleOrderPopup, {
                    order: order,
                    order_state: 'update',
                    sale_order_auto_confirm: this.pos.config.sale_order_auto_confirm,
                    sale_order_auto_delivery: this.pos.config.sale_order_auto_delivery,
                    sale_order_auto_invoice: this.pos.config.sale_order_auto_invoice,
                });
            }
        }
        else{
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('No SO Order Related To Update !'),
            })
        }

    },

});

