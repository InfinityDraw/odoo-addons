# -*- coding: utf-8 -*-
from odoo import models, api
import json
import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError
import logging

_logger = logging.getLogger(__name__)

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, force=True):
        """
        Suscribe a los partners y canales especificados al hilo de mensajes.
        Este método sobrescribe el método original para enviar una notificación de bienvenida a los nuevos suscriptores.
        Args:
            partner_ids (list): Lista de IDs de partners a suscribir.
            channel_ids (list): Lista de IDs de canales a suscribir.
            subtype_ids (list): Lista de IDs de subtipos de mensajes a los que suscribirse.
            force (bool): Si es True, fuerza la suscripción incluso si el partner o canal ya está suscrito.
        Returns:
            list: Lista de tuplas (partner_id, channel_id) que indican las nuevas suscripciones.
        """
        res = super(MailThread, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids, force=force)

        # Enviar una notificación de bienvenida a los nuevos suscriptores
        if partner_ids:
            self.message_post(
                body='¡Bienvenido a las notificaciones push de Odoo!',
                partner_ids=partner_ids,
                subtype_xmlid='mail.mt_comment',
                message_type='notification',
            )
        return res

    def _send_push_notification(self, message, msg_vals=None):
        """
        Envía una notificación push a través de FCM v1.
        Args:
            message (mail.message): El registro del mensaje.
            msg_vals (dict): Valores adicionales del mensaje.
        """
        config_settings = self.env['res.config.settings'].sudo().get_values()
        if not config_settings.get('push_notification') or not config_settings.get('firebase_config_file'):
            _logger.warning("Las notificaciones push no están habilitadas o falta la configuración de Firebase.")
            return

        try:
            # Verificar si el archivo de configuración de Firebase es un JSON válido
            try:
                cred_data = json.loads(config_settings['firebase_config_file'])
            except json.JSONDecodeError:
                _logger.error("El archivo de configuración de Firebase no es un JSON válido.")
                return

            # Inicializar Firebase Admin SDK (solo si no está ya inicializado)
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_data)
                firebase_admin.initialize_app(cred)
                _logger.info("Firebase Admin SDK inicializado.")

            # Obtener tokens de registro FCM
            registration_tokens = self._get_fcm_registration_tokens(message.partner_ids)
            if not registration_tokens:
                _logger.warning("No se encontraron tokens de registro FCM para los partners.")
                return

            # Crear un mensaje de notificación
            notification = messaging.Notification(
                title=msg_vals.get('subject') or message.subject,
                body=msg_vals.get('body') or message.body,
            )
            webpush_config = messaging.WebpushConfig(
                headers={"Urgency": "high"},
                notification=messaging.WebpushNotification(
                    title=msg_vals.get('subject') or message.subject,
                    body=msg_vals.get('body') or message.body,
                    icon="/static/img/icon-512x512.png",  # Ruta al icono dentro del módulo
                ),
            )

            # Crear y enviar mensajes a cada token de registro
            messages = [
                messaging.Message(
                    notification=notification,
                    webpush=webpush_config,
                    token=token,
                ) for token in registration_tokens
            ]
            
            # Enviar todos los mensajes a la vez
            response = messaging.send_all(messages)
            _logger.info(f"{response.success_count} mensajes de notificación enviados con éxito.")
            if response.failure_count > 0:
                _logger.warning(f"{response.failure_count} mensajes de notificación fallaron.")

        except FirebaseError as e:
            _logger.error(f"Error de Firebase al enviar mensaje de notificación: {e}")
        except Exception as e:
            _logger.error(f"Error general al enviar mensaje de notificación: {e}")

    def _notify_thread(self, message, msg_vals=None, **kwargs):
        """
        Envía notificaciones a los usuarios cuando se crea o actualiza un hilo de mensajes.
        """
        # Llama al método original para enviar notificaciones a través del bus de Odoo
        super(MailThread, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        self._send_push_notification(message, msg_vals)

    def _get_fcm_registration_tokens(self, partner_ids):
        """
        Obtiene los tokens de registro FCM de los partners.
        Args:
            partner_ids (res.partner): Objeto registro de partners.
        Returns:
            list: Lista de tokens de registro FCM.
        """
        return self.env['res.partner'].search([('id', 'in', partner_ids.ids)]).mapped('fcm_registration_token')
