from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class FcmController(http.Controller):
    """
    Controlador para manejar las solicitudes relacionadas con Firebase Cloud Messaging (FCM).
    """

    @http.route('/unicubevn_pwa/save_registration_token', type='json', auth='public', methods=['POST'], csrf=False)
    def save_registration_token(self, **kw):
        """
        Guarda el token de registro FCM del usuario en la base de datos.

        Args:
            kw: Diccionario de argumentos de la solicitud, incluyendo el token de registro.

        Returns:
            dict: Un diccionario JSON indicando el estado de la operación.
        """
        registration_token = kw.get('registration_token')
        if not registration_token:
            return {'status': 'error', 'message':
                    'Token de registro no proporcionado intentelo de nuevo o'
                     'pongase en contacto con el administrador con desarrollador'}

        try:
            # Buscar el partner asociado al usuario actual y guardar el token
            partner_id = request.env.user.partner_id.id
            if not partner_id:
                return {'status': 'error', 'message': 'Usuario no asociado a ningún partner'}

            partner = request.env['res.partner'].sudo().search([('id', '=', partner_id)])
            if not partner:
                return {'status': 'error', 'message': 'Partner no encontrado'}

            partner.write({'fcm_registration_token': registration_token})
            return {'status': 'success'}  # Devolver éxito si se guarda correctamente

        except ValidationError as e:  # Capturar ValidationError (errores de validación de Odoo)
            _logger.error(f"Error de validación al guardar el token de registro: {e}")
            return {'status': 'error', 'message': str(e)}  # Devolver el mensaje de error específico

        except Exception as e:  # Capturar otras excepciones (errores generales)
            _logger.error(f"Error interno al guardar el token de registro: {e}")
            return {'status': 'error', 'message': 'Error interno al guardar el token de registro'}