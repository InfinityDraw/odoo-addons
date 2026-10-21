/** @odoo-module */

import { Component, onMounted, useRef} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


export class SaleOrderPopup extends Component {
    static template = "ifdw_pos_sales_order_create_modify.SaleOrderPopup"
    static components = { Dialog };
    static props = [
        "close",
        "note?",
//        "signature?",
        "order",
        "pricelists",
        "order_state",
        "payment_partial_amount?",
        "payment_partial_method_id?",
        "pricelist_id?",
        "sale_order_auto_confirm",
        "sale_order_auto_delivery",
        "sale_order_auto_invoice",
    ];
    static defaultProps = {
        cancelText: _t("Close"),
        title: _t("Sale Order"),
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.dialog =  useService("dialog");
        this.report = useService("report");
        this.orm = useService("orm");
        this.currentOrder = this.pos.get_order();
        this.changes = {
            note: null,
//            signature: null,
            payment_partial_amount: 0,
            payment_partial_method_id: null,
            pricelist_id: this.currentOrder.pricelist ? this.currentOrder.pricelist.id : null,
            sale_order_auto_confirm: this.pos.config.sale_order_auto_confirm,
            sale_order_auto_delivery: this.pos.config.sale_order_auto_delivery,
            sale_order_auto_invoice: this.pos.config.sale_order_auto_invoice,
        }
//        this.signature_div = useRef("signature-div");
//        onMounted(this.mounted);
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtEnter: () => this.confirm(),
            triggerAtEscape: () => this.cancel(),
            state: this.changes,
        });
    }

//    mounted() {
//        var self = this;
//        $(this.signature_div.el).jSignature();
//        this.signed = false;
//        $(this.signature_div.el).bind('change', function (e) {
//            self.signed = true;
//            self.verifyChanges(e);
//        });
//    }

    OnChange(event) {
        let target_name = event.target.name;
        if (event.target.type == 'checkbox') {
            this.changes[event.target.name] = event.target.checked;
        } else {
            this.changes[event.target.name] = event.target.value;
        }
        if (target_name == 'payment_partial_amount') {
            this.changes[event.target.name] = parseFloat(event.target.value);
        }
        if (target_name == 'pricelist_id' || target_name == 'payment_partial_method_id') {
            this.changes[event.target.name] = parseInt(event.target.value);
        }
        this.verifyChanges(event)
    }

    verifyChanges(event) {
        let changes = this.changes;
        if (!this.env.utils.isValidFloat(changes.payment_partial_amount)) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Partial amount required number'),
            })
        }
//        const sign_datas = $(this.signature_div.el).jSignature("getData", "image");
//        if (this.pos.config.sale_order_required_signature) {
//            if (sign_datas && sign_datas[1] && this.signed) {
//                changes['signature'] = sign_datas[1];
////                this.orderUiState.isSuccessful = true;
////                this.orderUiState.hasNotice = _t('Signature succeed')
//            } else {
//                return this.dialog.add(ConfirmationDialog, {
//                    title: _t('Error'),
//                    body: _t('Please signature'),
//                })
//            }
//        } else {
//            return this.dialog.add(ConfirmationDialog, {
//                title: _t('Error'),
//                body: _t('Not required signature'),
//            })
//        }
        if (!changes.sale_order_auto_confirm || !changes.sale_order_auto_invoice){
            changes.payment_partial_amount = 0;
            changes.payment_partial_method_id = null;
        }
        if (changes.sale_order_auto_delivery && !changes.sale_order_auto_confirm){
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Please select auto confirm to be able to auto delivery'),
            })
        }
        if (changes.sale_order_auto_invoice && (!changes.sale_order_auto_confirm || !changes.sale_order_auto_delivery)){
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Please select auto confirm and auto delivery to be able to auto invoice'),
            })
        }
    }

    ValidateBeforeConfirm(){
        if (!this.changes.note){
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Please full fill information of order'),
            })
        }
    }
    GetCreateValues(){
        let order =  this.currentOrder;
        let value = {
            name: order.name,
            note: this.changes.note,
            origin: this.pos.config.name,
            partner_id: order.get_partner().id,
            pricelist_id: this.changes.pricelist_id,
            order_line: [],
//            signature:   this.changes.signature,
            signed_by: this.pos.user.name,
            payment_partial_amount: this.changes.payment_partial_amount,
            payment_partial_method_id: this.changes.payment_partial_method_id,
        }
        for (var i = 0; i < order.lines.length; i++) {
            var line = order.lines[i];
            var line_val = order._covert_pos_line_to_sale_line(line);
            value.order_line.push(line_val);
        }
        return value;
    }
    GetUpdateValues(){
        let order =  this.currentOrder;
        let value = {
            note: this.changes.note,
            partner_id: order.get_partner().id,
            pricelist_id: this.changes.pricelist_id,
            order_line: [],
//            signature:   this.changes.signature,
            payment_partial_amount: this.changes.payment_partial_amount,
            payment_partial_method_id: this.changes.payment_partial_method_id,
        }
        for (var i = 0; i < order.lines.length; i++) {
            var line = order.lines[i];
            var line_val = order._covert_pos_line_to_sale_line(line);
            value.order_line.push(line_val);
        }
        return value;
    }
    async DoAfter(result) {
        this.pos.removeOrder(this.currentOrder);
        this.pos.selectNextOrder();
        this.props.close()
        const confirmed = await ask(this.dialog, {
            body: _t("Are you want to print sale order %s report?", result.name),
        });
        if (confirmed) {
            return await this.report.doAction("sale.action_report_saleorder", [result.id]);
        }
        else{
              return false;
        }
    }

    async OnConfirmCreateSO() {
        await this.ValidateBeforeConfirm();
        if (this.changes.sale_order_auto_invoice && this.changes.payment_partial_amount <= 0) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Partial amount required bigger than 0'),
            })
        }
        let result = await this.orm.call(
            "sale.order",
             "create_from_pos_ui",
             [
                this.GetCreateValues(),
                this.changes.sale_order_auto_confirm,
                this.changes.sale_order_auto_delivery,
                this.changes.sale_order_auto_invoice
             ]
        )
        await this.DoAfter(result);
    }

    async OnConfirmUpdateSO() {
        await this.ValidateBeforeConfirm();
        if (this.changes.sale_order_auto_invoice && this.changes.payment_partial_amount <= 0) {
            return this.dialog.add(ConfirmationDialog, {
                title: _t('Error'),
                body: _t('Partial amount required bigger than 0'),
            })
        }
        const order_sale_id = this.currentOrder.get_orderlines().find((line) => line.sale_order_origin_id)?.sale_order_origin_id;
        if (order_sale_id){
            const sale_selected = await this.pos._getSaleOrder(order_sale_id.id);
            let result = await this.orm.call(
                "sale.order",
                "write_from_pos_ui",
                [
                    [sale_selected.id],
                    this.GetUpdateValues(),
                    this.changes.sale_order_auto_confirm,
                    this.changes.sale_order_auto_delivery,
                    this.changes.sale_order_auto_invoice
                ]
            );
            await this.DoAfter(result);
        }
    }

}
