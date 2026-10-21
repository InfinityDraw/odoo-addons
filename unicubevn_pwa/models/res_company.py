# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """Heredar esta clase para agregar la credencial de Firebase necesaria en la configuración
        configuración y uso de la función multiempresa"""
    _inherit = 'res.company'

    push_notification = fields.Boolean(string='Enable Push Notification',
                                        help="Habilitar notificación push web")