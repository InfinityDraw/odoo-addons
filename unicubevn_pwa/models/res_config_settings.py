# -*- coding: utf-8 -*-
import json
import logging
import firebase_admin

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    """
    Modelo para la configuración de notificaciones push a través de Firebase Cloud Messaging (FCM v1) y
    personalización de la aplicación web progresiva (PWA).
    """

    _inherit = 'res.config.settings'

    # Campos de configuración

    pwa_name = fields.Char(
        string="Nombre del PWA",
        help="Nombre de la aplicación web progresiva"
    )
    pwa_short_name = fields.Char(
        string="Nombre Corto del PWA",
        help="Nombre corto de la aplicación web progresiva"
    )
    pwa_background_color = fields.Char(
        string="Color de Fondo del PWA",
        default="#FFFFFF"
    )
    pwa_theme_color = fields.Char(
        string="Color del Tema del PWA",default="#FFFFFF"
    )
    pwa_icon = fields.Binary(
        string="Icono del PWA",
        readonly=False
    )
    push_notification = fields.Boolean(
        string='Habilitar Notificaciones Push',
        help="Habilita las notificaciones push web",
        readonly=False,
    )
    firebase_config_file = fields.Text(
        string="JSON de Firebase",
        required=True,
        help="Carga aquí el contenido del JSON de la cuenta de servicio de Firebase",
    )
    fcm_api_url = fields.Char(
        string="FCM API URL",
        default="https://fcm.googleapis.com/fcm/send",
        help="URL de la API de FCM para enviar mensajes",
        readonly=True,  # No es necesario que el usuario edite esta URL
    )
    vapid_private_key = fields.Char(
        string="VAPID Private Key",
        required=True,
        help="Clave privada VAPID (obtenida desde Firebase)",
    )
    vapid_public_key = fields.Char(
        string="VAPID Public Key",
        required=True,
        help="Clave pública VAPID (obtenida desde Firebase)",
    )

    @api.model
    def default_get(self, fields):
        """
        Obtiene los valores por defecto de los campos de configuración.
        """
        return super(ResConfigSettings, self).default_get(fields)

    @api.constrains('firebase_config_file')
    def _check_firebase_config_file(self):
        """
        Valida el contenido del JSON de la configuración de Firebase.
        """
        for record in self:
            if not record.firebase_config_file:
                raise ValidationError("Los datos del JSON de Firebase son obligatorios.")

        try:
            json_data = json.loads(record.firebase_config_file)
        except json.JSONDecodeError as error:
            raise ValidationError("El contenido cargado no es válido.") from error

        # Validar campos específicos de FCM v1
        required_fields = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_x509_cert_url"
        ]
        for field in required_fields:
            if field not in json_data:
                raise ValidationError(f"El campo '{field}' es obligatorio.")

    @api.model
    def test_connection(self, args):
        """
        Prueba la conexión con FCM enviando un mensaje de prueba a un topic.
        """
        if not self.push_notification or not self.firebase_config_file:
            raise ValidationError(_("Por favor, habilita las notificaciones push y carga el contenido del JSON de Firebase."))

        try:
            # Verificar si el contenido del JSON de Firebase es un formato válido
            try:
                cred_data = json.loads(self.firebase_config_file)
            except json.JSONDecodeError:
                raise ValidationError(_("El contenido del JSON de Firebase no tiene un formato válido."))
            
            # Inicializar Firebase Admin SDK (solo si no está ya inicializado)
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_data)
                firebase_admin.initialize_app(cred)
                _logger.info("Firebase Admin SDK inicializado.")

            # Crear un mensaje de notificación
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Prueba de Conexión",
                    body="Conexión establecida correctamente",
                ),
                webpush=messaging.WebpushConfig(
                    headers={"Urgency": "high"},
                    notification=messaging.WebpushNotification(
                        title="Prueba de Conexión",
                        body="Conexión establecida correctamente",
                        icon="/static/img/icon-512x512.png", # Ruta al icono dentro del modulo
                    ),
                ),
                topic='test',
            )

            # Enviar el mensaje y obtener la respuesta
            response = messaging.send(message)
            _logger.info(f"Mensaje enviado con éxito: {response}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("Conexión establecida correctamente"),
                    'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
                }
            }

        except FirebaseError as e:
            _logger.error(f"Error de Firebase al enviar mensaje de prueba: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("Error al conectar con Firebase: ") + str(e),
                    'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
                }
            }
        except Exception as e:
            _logger.error(f"Error general al conectar con Firebase: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _("Error desconocido al conectar con Firebase: ") + str(e),
                    'next': {'type': 'ir.actions.client', 'tag': 'reload_context'},
                }
            }

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icp = self.env['ir.config_parameter'].sudo()
        res.update(
            pwa_name=icp.get_param('web.web_app_name', default="Mi PWA"),
            pwa_short_name=icp.get_param('web.web_app_short_name', default="PWA"),
            pwa_background_color=icp.get_param('web.web_app_bg_color', default="#FFFFFF"),
            pwa_theme_color=icp.get_param('web.web_app_theme_color', default="#FFFFFF"),
            vapid_private_key=icp.get_param('web.vapid_private_key', default=""),
            vapid_public_key=icp.get_param('web.vapid_public_key', default=""),
            fcm_api_url=icp.get_param('web.fcm_api_url', default="https://fcm.googleapis.com/fcm/send"),
        )
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('web.web_app_name', self.pwa_name)
        icp.set_param('web.web_app_short_name', self.pwa_short_name)
        icp.set_param('web.web_app_bg_color', self.pwa_background_color)
        icp.set_param('web.web_app_theme_color', self.pwa_theme_color)
        icp.set_param('web.vapid_private_key', self.vapid_private_key)
        icp.set_param('web.vapid_public_key', self.vapid_public_key)
        icp.set_param('web.fcm_api_url', self.fcm_api_url)