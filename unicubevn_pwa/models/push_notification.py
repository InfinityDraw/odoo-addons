# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PushNotification(models.Model):
    """
    Modelo para almacenar los tokens de registro de los usuarios para el envío de notificaciones push a través de FCM v1.
    """
    _name = 'push.notification'
    _description = 'Web Push Notification'

    # Usuario asociado al token de registro
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade',
                              help="Usuario correspondiente de Firebase")
    
    # Token de registro del dispositivo generado por FCM v1
    fcm_registration_token = fields.Char(string='FCM Registration Token',
                                         help='Token de registro de Firebase')
