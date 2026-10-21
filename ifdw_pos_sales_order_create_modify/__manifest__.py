# -*- coding: utf-8 -*-
#############################################################################
#
#    Infinity Draw.
#
#    Copyright (C) 2024-HOY Infinity Draw (<https://infinitydraw.es>)
#    Autor: Fernan Nerd (<https://infinitydraw.es>)
#
#    Puedes modificarlo bajo los términos de GNU LESSER.
#    LICENCIA PÚBLICA GENERAL (LGPL v3), Versión 3.
#
#    Este programa se distribuye con la esperanza de que sea útil,
#    pero SIN NINGUNA GARANTÍA; sin siquiera la garantía implícita de
#    COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR.  Ver el
#    LICENCIA PÚBLICA GENERAL MENOR GNU (LGPL v3) para más detalles.
#
#    Debería haber recibido una copia de la LICENCIA PÚBLICA GENERAL MENOR DE GNU
#    (LGPL v3) junto con este programa.
#    En caso contrario, consulte <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': "POS Sales Order Create/Modify",
    'summary': """Create/Modify Sales Order from POS""",
    'description': """POS Sales Order Create/Modify""",

    'category': 'Sales/Point of Sale',
    "version": "18.0.0.1.1",
    "website": "https://github.com/Fernando-Draw/ifdw_pos_sales_order_create_modify",
    "author": "Fernando-Draw",
    "maintainers": ["Fernando-Draw"],
    "license": "AGPL-3",
    'depends': ['sale_stock', 'pos_sale'],
    'data': [
        # Views
        'views/pos_config.xml',
        'views/sale_order.xml',
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "ifdw_pos_sales_order_create_modify/static/src/**/*"
        ]
    },

    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
