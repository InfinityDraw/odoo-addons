# -*- coding: utf-8 -*-
import base64
import io
import sys

from PIL import Image

from odoo import _, api, exceptions, fields, models
from odoo.tools.mimetypes import guess_mimetype

class ResCompany(models.Model):
    _inherit = 'res.company'

    push_notification = fields.Boolean(
        string="Habilitar Notificaciones Push"
    )
    firebase_config_file = fields.Text(
        string="Archivo de Configuración de Firebase"
    )
    vapid_private_key = fields.Char(
        string="Clave Privada VAPID"
    )
    vapid_public_key = fields.Char(
        string="Clave Pública VAPID"
    )
    fcm_api_url = fields.Char(
        string="URL de la API FCM", default="https://fcm.googleapis.com/fcm/send"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _pwa_icon_url_base = "/unicubevn_pwa/img/"

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
        string="Color del Tema del PWA",
        default="#FFFFFF"
    )
    pwa_icon = fields.Binary(
        string="Icono del PWA",
        readonly=False,
        help="Icono de la aplicación web progresiva"
    )
    push_notification = fields.Boolean(
        string="Habilitar Notificaciones Push",
        help="Habilitar notificaciones push web",
        related='company_id.push_notification',
        readonly=False,
    )
    firebase_config_file = fields.Text(
        string="Archivo de Configuración de Firebase",
        help="Archivo JSON de configuración de Firebase",
        related="company_id.firebase_config_file",
        readonly=False,
    )
    vapid_private_key = fields.Char(
        string="Clave Privada VAPID",
        help="Clave privada VAPID",
        related='company_id.vapid_private_key',
        readonly=False,
    )
    vapid_public_key = fields.Char(
        string="Clave Pública VAPID",
        help="Clave pública VAPID",
        related="company_id.vapid_public_key",
        readonly=False,
    )
    fcm_api_url = fields.Char(
        string="URL de la API FCM",
        default="https://fcm.googleapis.com/fcm/send",
        related='company_id.fcm_api_url',
        readonly=False,
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icp = self.env['ir.config_parameter'].sudo()
        res.update(
            pwa_name=icp.get_param(
                'web.web_app_name',
                default="Mi APP Web"
            ),
            pwa_short_name=icp.get_param(
                'web.web_app_short_name',
                default="Nombre Corto de la App"
            ),
            pwa_background_color=icp.get_param(
                'web.web_app_bg_color',
                default="#FFFFFF"
            ),
            pwa_theme_color=icp.get_param(
                'web.web_app_theme_color',
                default="#FFFFFF"
            ),
        )
        pwa_icon_ir_attachment = (
            self.env["ir.attachment"]
            .sudo()
            .search([("url", "like", self._pwa_icon_url_base + ".")])
        )
        res['pwa_icon'] = pwa_icon_ir_attachment.datas if pwa_icon_ir_attachment else False
        return res

    @staticmethod
    def _unpack_icon(icon):
        decoded_icon = base64.b64decode(icon)
        icon_bytes = io.BytesIO(decoded_icon)
        return Image.open(icon_bytes)

    def _write_icon_to_attachment(self, extension, mimetype, size=None):
        url = self._pwa_icon_url_base + extension
        icon = self.pwa_icon
        name = 'default'
        if size:
            image = self._unpack_icon(icon)
            resized_image = image.resize(size)
            icon_bytes_output = io.BytesIO()
            resized_image.save(icon_bytes_output, format=extension.lstrip(".").upper())
            icon = base64.b64encode(icon_bytes_output.getvalue())
            url = "{}icon-{}x{}{}".format(
                self._pwa_icon_url_base,
                str(size[0]),
                str(size[1]),
                extension,
            )
            name = f"{str(size[0])}x{str(size[1])}"
        existing_attachment = self.env["ir.attachment"].sudo().search([("url", "like", url)])
        values = {
            "datas": icon,
            "db_datas": icon,
            "url": url,
            "name": name,
            "type": "binary",
            "mimetype": mimetype,
        }
        if existing_attachment:
            existing_attachment.sudo().write(values)
        else:
            self.env["ir.attachment"].sudo().create(values)

    @api.model
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param(
            'web.web_app_name',
            self.pwa_name
        )
        icp.set_param(
            'web.web_app_short_name',
            self.pwa_short_name
        )
        icp.set_param(
            'web.web_app_bg_color',
            self.pwa_background_color
        )
        icp.set_param(
            'web.web_app_theme_color',
            self.pwa_theme_color
        )
        pwa_icon_ir_attachments = (
            self.env["ir.attachment"].sudo().search(
                [("url", "like", self._pwa_icon_url_base)]
            )
        )
        if not self.pwa_icon:
            if pwa_icon_ir_attachments:
                pwa_icon_ir_attachments.unlink()
            return res
        if sys.getsizeof(self.pwa_icon) > 2196608:
            raise exceptions.UserError(_("You can't upload a file with more than 2 MB."))
        decoded_pwa_icon = base64.b64decode(self.pwa_icon)
        pwa_icon_mimetype = guess_mimetype(decoded_pwa_icon)
        pwa_icon_extension = "." + pwa_icon_mimetype.split("/")[-1].split("+")[0]
        if not pwa_icon_mimetype.startswith(
            "image/svg") and not pwa_icon_mimetype.startswith(
            "image/png"
        ):
            raise exceptions.UserError(
                _("You can only upload SVG or PNG files. Found: %s.") % pwa_icon_mimetype
            )
        if pwa_icon_ir_attachments:
            pwa_icon_ir_attachments.unlink()
        self._write_icon_to_attachment(pwa_icon_extension, pwa_icon_mimetype)
        if pwa_icon_extension != ".svg":
            if self._unpack_icon(self.pwa_icon).size < (512, 512):
                raise exceptions.UserError(
                    _("You can only upload PNG files bigger than 512x512"))
            for size in [
                (128, 128),
                (144, 144),
                (152, 152),
                (192, 192),
                (256, 256),
                (512, 512)
            ]:
                self._write_icon_to_attachment(
                    pwa_icon_extension, pwa_icon_mimetype, size=size
                )
        icp.set_param('web.fcm_api_url', self.fcm_api_url)
        return res