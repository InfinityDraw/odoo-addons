# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

class PwaMain(http.Controller):

    # Ruta para obtener la clave VAPID pública
    @http.route('/unicubevn_pwa/vapid_public_key', type='json', auth='public')
    def vapid_public_key(self):
        """
        Obtiene la clave VAPID pública desde la configuración de Odoo.
        Esta clave es necesaria para que el service worker pueda registrar el dispositivo en FCM v1.
        
        Returns:
            dict: Un diccionario JSON con la clave VAPID pública.
        """
        try:
            config = request.env['res.config.settings'].sudo().get_values()   # Obtener el modelo de configuración
            vapid_public_key = config.get('vapid_public_key')  # Acceder al valor de la clave VAPID pública

            if not vapid_public_key:
                raise ValidationError("La clave VAPID pública no está configurada. Por favor, contacta con el administrador.")

            return {'vapid_public_key': vapid_public_key}  # Devolver la clave en formato JSON
        
        except ValidationError as e:
            return {'status': 'error', 'message': str(e)}
        
        except Exception as e:
            return {'status': 'error', 'message':
                    'Error al obtener la clave VAPID pública'}  # Mensaje de error al intentar obtener la clave VAPID pública