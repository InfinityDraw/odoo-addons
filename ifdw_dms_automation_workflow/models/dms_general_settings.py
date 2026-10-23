# -*- coding: utf-8 -*-
# Copyright 2026 Infinity Draw (https://infinitydraw.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
import os
from odoo import api, fields, models, _
from .dms_automation import (
    CAD_EXTENSIONS,
    SIGNATURE_NAME_PATTERNS,
    MAX_LINUX_BASE_FILENAME_CHARS,
)

_logger = logging.getLogger(__name__)

DEFAULT_GENERAL_STORAGE_NAME = 'Almacenamiento general Automatizado del Chatter'

DEFAULT_GENERAL_FOLDERS = [
    (10, '01_images', '01 - Imágenes', 'jpg, jpeg, jpe, jfif, png, webp, avif, heic, heif, dng, raw, cr2, nef, arw, bmp, tif, tiff, gif', False),
    (20, '02_videos', '02 - Videos', 'mp4, mov, m4v, avi, mkv, webm, 3gp, 3g2, mpeg, mpg, wmv, flv', False),
    (30, '03_audios', '03 - Audios', 'ogg, opus, m4a, mp3, wav, aac, amr, wma, flac', False),
    (40, '04_docs', '04 - Documentos y PDF', 'pdf, doc, docx, odt, rtf, txt, md, ppt, pptx, odp, epub', False),
    (50, '05_tables', '05 - Tablas, Datos y CSV', 'xls, xlsx, ods, csv, tsv, xml, json, yaml, yml, parquet, db, sqlite', False),
    (60, '06_vector', '06 - Dibujos y Archivos Vectoriales', 'svg, ai, eps, cdr, psd, indd, fig, xcf, afdesign, wmf, emf', False),
    (70, '07_3d', '07 - 3D', 'dwg, dxf, dwf, ifc, rvt, skp, bc3, stl, obj, fbx, step, stp, iges, igs, blend, 3ds, gltf, glb', False),
    (80, '08_dev', '08 - Desarrollo y Programación', 'py, js, ts, html, css, scss, php, sql, sh, bat, ps1, c, cpp, h, java, cs, go, rs, vue, jsx, tsx', False),
    (90, '09_archives', '09 - Comprimidos y ZIP', 'zip, rar, 7z, tar, gz, bz2, tgz, xz, iso, dmg', False),
    (100, '10_other', '10 - Otros', '', True),
]


class IfdwDmsGeneralFolderLine(models.Model):
    _name = 'ifdw.dms.general.folder.line'
    _description = 'Carpeta Estándar del Almacenamiento General DMS'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Orden', default=10)
    code = fields.Char(string='Código Interno', readonly=True)
    name = fields.Char(
        string='Nombre de la Carpeta',
        required=True,
        help='Nombre de la carpeta raíz dentro del Almacenamiento General. Si lo cambias aquí, se renombrará automáticamente en el DMS.',
    )
    extensions = fields.Char(
        string='Extensiones admitidas (separadas por comas)',
        help='Lista de extensiones sin punto (ej. "jpg, png, webp"). La carpeta 10 - Otros actúa además como cajón de sastre para cualquier extensión no listada en las anteriores.',
    )
    is_catch_all = fields.Boolean(
        string='Es Cajón de Sastre (Otros)',
        default=False,
        readonly=True,
        help='Recibe automáticamente cualquier archivo cuya extensión no coincida con las carpetas anteriores.',
    )
    directory_id = fields.Many2one(
        'dms.directory',
        string='Carpeta DMS Vinculada',
        readonly=True,
        ondelete='set null',
        help='Referencia directa a la carpeta física en el DMS para mantener el vínculo aunque la renombres.',
    )

    @api.model
    def _register_hook(self):
        res = super()._register_hook()
        try:
            self._ensure_default_10_lines()
        except Exception as e:
            _logger.warning("No se pudieron inicializar las 10 carpetas estándar DMS: %s", e)
        return res

    @api.model
    def _ensure_default_10_lines(self):
        existing_codes = set(self.sudo().search([]).mapped('code'))
        vals_to_create = []
        for seq, code, folder_name, exts, is_catch in DEFAULT_GENERAL_FOLDERS:
            if code not in existing_codes:
                vals_to_create.append({
                    'sequence': seq,
                    'code': code,
                    'name': folder_name,
                    'extensions': exts,
                    'is_catch_all': is_catch,
                })
        if vals_to_create:
            self.sudo().create(vals_to_create)

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals and not self.env.context.get('skip_ifdw_general_dir_rename'):
            for rec in self:
                if rec.directory_id and rec.directory_id.exists():
                    try:
                        rec.directory_id.sudo().write({'name': rec.name})
                    except Exception as e:
                        _logger.warning("No se pudo renombrar la carpeta general DMS %s: %s", rec.name, e)
        return res

    @api.model
    def _get_or_create_default_access_groups(self):
        ICP = self.env['ir.config_parameter'].sudo()
        AccessGroup = self.env['dms.access.group'].sudo()
        raw_ids = ICP.get_param('ifdw_dms.general_access_group_ids', '')
        group_ids = [int(x) for x in raw_ids.split(',') if x.strip().isdigit()]
        groups = AccessGroup.browse(group_ids).exists()
        if groups:
            return groups

        # Si el usuario no eligió grupos, reutilizar o crear uno por defecto para Usuarios Internos
        default_group = AccessGroup.search([('name', '=', 'Acceso General Chatter DMS')], limit=1)
        if not default_group:
            internal_group = self.env.ref('base.group_user', raise_if_not_found=False)
            vals = {
                'name': 'Acceso General Chatter DMS',
                'perm_create': True,
                'perm_write': True,
                'perm_unlink': True,
            }
            if internal_group and 'group_ids' in AccessGroup._fields:
                vals['group_ids'] = [(4, internal_group.id)]
            default_group = AccessGroup.create(vals)
        ICP.set_param('ifdw_dms.general_access_group_ids', str(default_group.id))
        return default_group

    @api.model
    def _sync_general_storage_and_folders(self):
        self._ensure_default_10_lines()
        ICP = self.env['ir.config_parameter'].sudo()
        Storage = self.env['dms.storage'].sudo()
        Directory = self.env['dms.directory'].sudo()

        storage_name = (ICP.get_param('ifdw_dms.general_storage_name') or DEFAULT_GENERAL_STORAGE_NAME).strip()
        storage_id = int(ICP.get_param('ifdw_dms.general_storage_id') or 0)
        storage = Storage.browse(storage_id).exists() if storage_id else Storage.browse()

        if not storage:
            storage = Storage.search([('name', '=', storage_name)], limit=1)
        if not storage:
            storage = Storage.create({
                'name': storage_name,
                'save_type': 'file',
            })
        elif storage.name != storage_name:
            storage.write({'name': storage_name})

        ICP.set_param('ifdw_dms.general_storage_id', str(storage.id))
        access_groups = self._get_or_create_default_access_groups()

        for line in self.sudo().search([], order='sequence, id'):
            dir_rec = line.directory_id.exists() if line.directory_id else Directory.browse()
            if dir_rec and dir_rec.storage_id != storage:
                dir_rec = Directory.browse()

            if not dir_rec:
                dir_rec = Directory.search([
                    ('storage_id', '=', storage.id),
                    ('is_root_directory', '=', True),
                    ('name', '=', line.name),
                ], limit=1)

            if not dir_rec:
                dir_vals = {
                    'name': line.name,
                    'storage_id': storage.id,
                    'is_root_directory': True,
                }
                if access_groups and 'group_ids' in Directory._fields:
                    dir_vals['group_ids'] = [(6, 0, access_groups.ids)]
                dir_rec = Directory.create(dir_vals)
            else:
                update_vals = {}
                if dir_rec.name != line.name:
                    update_vals['name'] = line.name
                if access_groups and 'group_ids' in Directory._fields:
                    update_vals['group_ids'] = [(6, 0, access_groups.ids)]
                if update_vals:
                    dir_rec.write(update_vals)

            if line.directory_id != dir_rec:
                line.with_context(skip_ifdw_general_dir_rename=True).write({'directory_id': dir_rec.id})

        return storage

    @api.model
    def _classify_attachment_global(self, attachment, record):
        """Enruta un adjunto de Chatter sin regla específica al Almacenamiento General."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('ifdw_dms.enable_global_chatter_routing') != 'True':
            return False
        if not attachment.datas:
            return False

        fname_orig = attachment.name or 'archivo'
        fname_low = fname_orig.lower()
        base_name, ext_dot = os.path.splitext(fname_orig)
        ext_low = ext_dot.lstrip('.').lower()
        mimetype_low = (attachment.mimetype or '').lower()

        # Filtro básico anti-firmas de correo para no inundar 01 - Imágenes con iconos pequeños
        is_cad_or_svg = ext_low in CAD_EXTENSIONS or ext_low == 'svg' or 'svg' in mimetype_low
        if not is_cad_or_svg:
            for pat in SIGNATURE_NAME_PATTERNS:
                if pat in fname_low:
                    return False
            if mimetype_low.startswith('image/') and 0 < (attachment.file_size or 0) < (20 * 1024):
                return False

        storage = self._sync_general_storage_and_folders()
        if not storage:
            return False

        lines = self.sudo().search([], order='sequence, id')
        matched_line = False
        catch_all_line = lines.filtered(lambda l: l.is_catch_all)[:1]

        for line in lines:
            exts = {e.strip().lstrip('.').lower() for e in (line.extensions or '').split(',') if e.strip()}
            if ext_low and ext_low in exts:
                matched_line = line
                break

        if not matched_line:
            matched_line = catch_all_line or lines[-1:]
        if not matched_line or not matched_line.directory_id:
            return False

        target_dir = matched_line.directory_id.sudo()

        # Auto-renombrado fijo y transparente: [NombreOriginal]_[AAMMDD-HHMM].ext
        dt_local = fields.Datetime.context_timestamp(self, attachment.create_date or fields.Datetime.now())
        suffix_dt = dt_local.strftime('%y%m%d-%H%M')
        max_base = MAX_LINUX_BASE_FILENAME_CHARS - len(suffix_dt) - 1
        clean_base = base_name[:max_base].rstrip('_- ') if len(base_name) > max_base else base_name
        final_name = f"{clean_base}_{suffix_dt}{ext_dot}"

        DmsFile = self.env['dms.file'].sudo()
        existing = DmsFile.with_context(ifdw_disable_child_of_directory=True).search([
            ('directory_id', '=', target_dir.id),
            '|', ('name', '=', final_name), ('ifdw_source_attachment_id', '=', attachment.id),
        ], limit=1)
        if existing:
            return False

        # Etiqueta automática con el nombre de la aplicación / modelo de Odoo (ej. "Contacto", "Vehículo")
        IrModel = self.env['ir.model'].sudo()
        model_rec = IrModel.search([('model', '=', record._name)], limit=1)
        app_tag_name = (model_rec.name if model_rec else getattr(record, '_description', record._name) or record._name).strip()[:50]

        Tag = self.env['dms.tag'].sudo()
        tag = Tag.search([('name', '=', app_tag_name)], limit=1)
        if not tag:
            tag = Tag.create({'name': app_tag_name})

        dms_file = DmsFile.create({
            'name': final_name,
            'directory_id': target_dir.id,
            'content': attachment.datas,
            'ifdw_source_attachment_id': attachment.id,
            'tag_ids': [(4, tag.id)],
        })
        attachment.sudo().with_context(skip_ifdw_attachment_hook=True).write({'x_ifdw_dms_synced': True})

        return {
            'dms_file': dms_file,
            'original_name': fname_orig,
            'dms_name': dms_file.name,
            'dest_folder_name': f"{storage.name} / {target_dir.name}",
            'user_name': (attachment.create_uid.name if attachment.create_uid else False) or self.env.user.name,
        }


class ResConfigSettingsDmsGeneral(models.TransientModel):
    _inherit = 'res.config.settings'

    ifdw_enable_global_chatter_dms = fields.Boolean(
        string='Capturar automáticamente archivos de cualquier Chatter sin regla específica',
        config_parameter='ifdw_dms.enable_global_chatter_routing',
        help='Si está activo, cualquier archivo que se suelte en un Chatter que no tenga una regla en Automatización DMS se guardará y clasificará automáticamente por su extensión en el almacenamiento general exclusivo.',
    )
    ifdw_general_storage_name = fields.Char(
        string='Nombre del Almacenamiento General Exclusivo',
        config_parameter='ifdw_dms.general_storage_name',
        default=DEFAULT_GENERAL_STORAGE_NAME,
        help='Nombre del almacenamiento exclusivo que se creará automáticamente al guardar estos ajustes.',
    )
    ifdw_general_storage_id = fields.Many2one(
        'dms.storage',
        string='Almacenamiento General Creado',
        compute='_compute_ifdw_general_dms_info',
        readonly=True,
    )
    ifdw_general_access_group_ids = fields.Many2many(
        'dms.access.group',
        string='Grupos de acceso DMS para este Almacenamiento',
        help='Define qué grupos de acceso DMS podrán ver y gestionar las 10 carpetas estándar del almacenamiento general.',
    )

    def _compute_ifdw_general_dms_info(self):
        ICP = self.env['ir.config_parameter'].sudo()
        storage_id = int(ICP.get_param('ifdw_dms.general_storage_id') or 0)
        storage = self.env['dms.storage'].sudo().browse(storage_id).exists() if storage_id else False
        for rec in self:
            rec.ifdw_general_storage_id = storage.id if storage else False

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        self.env['ifdw.dms.general.folder.line'].sudo()._ensure_default_10_lines()
        raw_ids = ICP.get_param('ifdw_dms.general_access_group_ids', '')
        group_ids = [int(x) for x in raw_ids.split(',') if x.strip().isdigit()]
        valid_groups = self.env['dms.access.group'].sudo().browse(group_ids).exists()
        res.update({
            'ifdw_general_storage_name': ICP.get_param('ifdw_dms.general_storage_name') or DEFAULT_GENERAL_STORAGE_NAME,
            'ifdw_general_access_group_ids': [(6, 0, valid_groups.ids)],
        })
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        storage_name = (self.ifdw_general_storage_name or DEFAULT_GENERAL_STORAGE_NAME).strip()
        ICP.set_param('ifdw_dms.general_storage_name', storage_name)
        ICP.set_param(
            'ifdw_dms.general_access_group_ids',
            ','.join(str(gid) for gid in self.ifdw_general_access_group_ids.ids),
        )
        if self.ifdw_enable_global_chatter_dms:
            self.env['ifdw.dms.general.folder.line'].sudo()._sync_general_storage_and_folders()

    def action_open_general_folder_lines(self):
        self.env['ifdw.dms.general.folder.line'].sudo()._ensure_default_10_lines()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configurar las 10 Carpetas y Extensiones del Almacenamiento General'),
            'res_model': 'ifdw.dms.general.folder.line',
            'view_mode': 'list',
            'target': 'new',
        }
