/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {

    _covert_pos_line_to_sale_line: function (line) {
        let line_val = {
            product_id: line.product_id.id,
            price_unit: line.price_unit,
            product_uom_qty: line.qty,
        };
        if (line.discount) {
            line_val['discount'] = line.discount
        }
        else {
            line_val['discount'] = 0
        }

        if (line.uom_id) {
            line_val['product_uom'] = line.uom_id
        }
         else {
            line_val['product_uom'] = line.product_id.uom_id.id
        }
//        if (line.variants) {
//            line_val['variant_ids'] = [[6, false, []]];
//            for (let j = 0; j < line.variants.length; j++) {
//                let variant = line.variants[j];
//                line_val['variant_ids'][0][2].push(variant.id)
//            }
//        }
        if (line.tax_ids) {
            line_val['tax_id'] = line.tax_ids.ids;
        }
        if (line.customer_note) {
            line_val['note'] = line.customer_note;
        }
        return [0, 0, line_val];
    },

    select_orderline(line) {
        const res = super.select_orderline(...arguments);
        if (line && line.sale_order_origin_id) {
            line.order_id['sale_id'] = line.sale_order_origin_id.id
        }
        return res
    }

})
