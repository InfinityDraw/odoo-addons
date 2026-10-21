# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'  # Heredar del modelo base 'res.partner'

    # Campo para almacenar el token de registro FCM del usuario
    fcm_registration_token = fields.Char(string="FCM Registration Token",
                                        help="Token de registro FCM del dispositivo del usuario")
