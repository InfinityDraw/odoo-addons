# -*- coding: utf-8 -*-
# Copyright 2026 Infinity Draw (https://infinitydraw.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import logging
import os
import re
from markupsafe import Markup, escape
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {
    'jpg', 'jpeg', 'jpe', 'jfif', 'png', 'webp', 'avif',
    'heic', 'heif', 'dng', 'raw', 'cr2', 'nef', 'arw',
    'bmp', 'tif', 'tiff', 'gif',
}
VIDEO_EXTENSIONS = {
    'mp4', 'mov', 'm4v', 'avi', 'mkv', 'webm', '3gp', '3g2', 'mpeg', 'mpg', 'wmv',
}
AUDIO_EXTENSIONS = {
    'ogg', 'opus', 'm4a', 'mp3', 'wav', 'aac', 'amr', 'wma',
}
CAD_EXTENSIONS = {
    'dwg', 'dxf', 'dwf', 'ifc', 'rvt', 'skp', 'bc3', 'bak', 'plt',
}
DOC_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'odt', 'ods', 'odp', 'csv', 'txt', 'rtf',
}
ARCHIVE_EXTENSIONS = {
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'tgz',
}
SIGNATURE_NAME_PATTERNS = (
    'image001.', 'image002.', 'image003.', 'image004.',
    'logo_firma', 'linkedin.', 'facebook.', 'instagram.',
)
MAX_LINUX_BASE_FILENAME_CHARS = 180


class IfdwDmsAutomation(models.Model):
    _name = 'ifdw.dms.automation'
    _description = 'Regla de Automatización DMS'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de evaluación de las reglas de automatización DMS.',
    )
    name = fields.Char(
        string='Nombre de la Regla',
        required=True,
        help='Nombre identificativo de esta regla de automatización (ej. "Archivos de CRM" o "Archivos de Proyectos").',
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está desmarcado, esta regla de automatización no se ejecuta, evitando tener que borrarla.',
    )

    template_id = fields.Many2one(
        'dms.field.template',
        string='Seleccionar "Plantilla DMS embeb."',
        required=True,
        ondelete='restrict',
        help='Selecciona una de las Plantillas DMS embebidas previamente configuradas en Documentos > Configuración > Organizar > Plantillas DMS embebidas.',
    )
    storage_id = fields.Many2one(
        'dms.storage',
        string='Almacenamiento de plantilla',
        related='template_id.storage_id',
        readonly=True,
        store=True,
        help='Almacenamiento físico (Filestore) heredado automáticamente de la Plantilla DMS embebida seleccionada (Solo lectura).',
    )
    parent_directory_id = fields.Many2one(
        'dms.directory',
        string='Carpeta padre de destino',
        related='template_id.parent_directory_id',
        readonly=True,
        store=True,
        help='Carpeta maestra donde se crearán las carpetas clonadas de cada registro (Heredada de la Plantilla DMS embebida).',
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Modelo de plantilla',
        related='template_id.model_id',
        readonly=True,
        store=True,
        help='Modelo principal de Odoo al que está asociada la Plantilla DMS embebida seleccionada (Solo lectura).',
    )
    model_name = fields.Char(
        string='Nombre Técnico Modelo',
        related='template_id.model_id.model',
        readonly=True,
        store=True,
    )
    group_ids = fields.Many2many(
        'dms.access.group',
        string='Grupos de plantilla',
        compute='_compute_template_info',
        help='Grupos de acceso del DMS configurados en la Plantilla DMS embebida seleccionada (Solo lectura).',
    )
    template_root_dir_id = fields.Many2one(
        'dms.directory',
        string='Carpeta Raíz del Molde',
        compute='_compute_template_info',
        store=True,
        readonly=False,
        domain="[('storage_id', '=', storage_id)]",
        help='Carpeta en Documentos > Carpetas que actúa como molde oficial de esta Plantilla DMS embebida. Se autocompleta sola, pero puedes cambiarla manualmente.',
    )
    auto_clone_on_create = fields.Boolean(
        string='Clonar plantilla automáticamente con cada nuevo registro',
        default=True,
        help='Clona automáticamente el árbol de carpetas de la Plantilla DMS embebida cada vez que se crea un registro que cumpla el filtro.',
    )
    filter_domain = fields.Char(
        string='Filtro de registros (A cuáles SÍ / NO crear carpeta)',
        default='[]',
        help='Define qué registros del modelo configurado en la plantilla de DMS deben generar una carpeta automáticamente (ej. excluir la etapa Plantillas en Proyectos o excluir registros con un estado específico).',
    )
    show_smart_button = fields.Boolean(
        string='Mostrar botones Inteligentes [Documentos]',
        default=True,
        help='Muestra el botón inteligente Documentos en la barra superior del formulario del modelo principal y de sus modelos satélite.',
    )
    auto_rename_chatter = fields.Boolean(
        string='Auto-renombrado de archivos subidos al Chatter',
        default=True,
        help='Renombra automáticamente los archivos que entren por el clip del Chatter para evitar nombres repetidos desde móviles.',
    )
    rename_format = fields.Selection(
        selection=[
            ('fmt_0_orig', '[NombreOriginal]'),
            ('fmt_0_seq', '[001]-[NombreOriginal]'),
            ('fmt_1', '[AAAAMMDD-HHMM]_[Origen/Tarea]_[NombreOriginal]'),
            ('fmt_2', '[AA-MM-DD]_[Origen/Tarea]_[NombreOriginal]'),
            ('fmt_3', '[NombreOriginal]_[Origen/Tarea]_[AA-MM-DD]'),
            ('fmt_4', '[Origen/Tarea]_[AA-MM-DD]_[NombreOriginal]'),
            ('fmt_5', '[AA-MM-DD]_[Usuario]_[Origen/Tarea]_[NombreOriginal]'),
        ],
        string='Formato',
        default='fmt_1',
        required=True,
        help='Estructura con la que se renombrarán los archivos al guardarse en su subcarpeta del DMS.',
    )
    filter_small_images = fields.Boolean(
        string='Filtro anti-archivos basura chicos (Firmas Email)',
        default=True,
        help='Descarta imágenes diminutas incrustadas en firmas de correo electrónico. Los archivos vectoriales (.svg) y planos (.dwg) nunca son bloqueados.',
    )
    min_image_size_kb = fields.Integer(
        string='Ignorar imágenes menores a (KB)',
        default=20,
        help='Tamaño mínimo en Kilobytes (KB) para aceptar una imagen bitmap desde el Chatter (Rango: 1 KB a 100 KB, por defecto 20 KB).',
    )
    sync_unlink_chatter = fields.Boolean(
        string='Sincronizar papelera Chatter <-> DMS',
        default=True,
        help='Si un usuario elimina manualmente un archivo adjunto desde la papelera del Chatter, se elimina también su copia vinculada en este almacenamiento DMS (Se respeta los archivos bloqueados con candado de seguridad del DMS).',
    )

    classify_line_ids = fields.One2many(
        'ifdw.dms.automation.classify.line',
        'automation_id',
        string='Reglas de Auto-clasificación desde Chatter',
        copy=True,
        help='Define qué tipos de archivo subidos al Chatter van a cada subcarpeta de la plantilla y qué Categoría DMS se les asigna.',
    )
    satellite_line_ids = fields.One2many(
        'ifdw.dms.automation.satellite.line',
        'automation_id',
        string='Reglas de Modelos Extra (Satélites)',
        copy=True,
        help='Añade otros modelos de Odoo (Tareas, Pedidos de Venta, Facturas) para que sus adjuntos del Chatter vayan a la carpeta del registro principal.',
    )

    enable_file_movement = fields.Boolean(
        string='Activar movimiento/copia de archivos entre flujos',
        default=False,
        help='Conecta esta regla con otra regla de Automatización DMS. Soporta flujos encadenados (A -> B -> C) manteniendo separados los canales de Entrada y Salida.',
    )
    movement_role = fields.Selection(
        selection=[
            ('as_dest', 'Canal de Entrada: Recibir archivos desde una Regla de Origen (Ej. Estoy en Proyectos y recibo desde CRM)'),
            ('as_source', 'Canal de Salida: Enviar archivos hacia una Regla de Destino (Ej. Estoy en CRM y envío hacia Proyectos)'),
        ],
        string='Modo de Configuración (Espejo)',
        default='as_dest',
        required=True,
        help='Puedes configurar tanto el Canal de Entrada (de quién recibes) como el Canal de Salida (a quién envías) sin que uno machaque al otro.',
    )

    source_automation_id = fields.Many2one(
        'ifdw.dms.automation',
        string='Regla Automatización DMS de Origen',
        domain="[('id', '!=', id)]",
        ondelete='set null',
        help='Regla de Automatización DMS de la que provienen los archivos iniciales (ej. Archivos de CRM).',
    )
    in_source_root_dir_id = fields.Many2one(
        'dms.directory',
        string='Carpeta Molde Origen (Entrada)',
        compute='_compute_effective_movement_roots',
        readonly=True,
    )
    in_dest_root_dir_id = fields.Many2one(
        'dms.directory',
        string='Carpeta Molde Destino (Entrada)',
        compute='_compute_effective_movement_roots',
        readonly=True,
    )
    in_dest_model_id = fields.Many2one(
        'ir.model',
        string='Modelo Destino (Entrada)',
        compute='_compute_effective_movement_roots',
        readonly=True,
    )
    origin_link_field_id = fields.Many2one(
        'ir.model.fields',
        string='Campo de enlace en el Destino (Entrada)',
        domain="[('model_id', '=', in_dest_model_id), ('ttype', '=', 'many2one')]",
        ondelete='set null',
        help='Campo del modelo de destino que lo conecta con el origen (se rellena automáticamente; ej. Pedido de venta en Proyectos).',
    )
    after_move_action = fields.Selection(
        selection=[
            ('copy_keep', 'Opción 1: Copiar los archivos al destino manteniendo también los originales en su carpeta de origen.'),
            ('move_delete_dir', 'Opción 2: Mover los archivos al destino y borrar los datos residuales del origen (borra los archivos y carpetas en origen).'),
            ('move_keep_dir', 'Opción 3: Mover los archivos al destino y borrar solo archivos residuales del origen (deja carpetas vacías en origen).'),
        ],
        string='Acción tras trasladar archivos (Entrada)',
        default='copy_keep',
        required=True,
    )
    post_chatter_summary = fields.Boolean(
        string='Publicar nota de trazabilidad en el Chatter (Entrada)',
        default=True,
    )
    trace_model_ids = fields.Many2many(
        'ir.model',
        'ifdw_dms_automation_trace_model_rel',
        'automation_id',
        'model_id',
        string='Modelos donde publicar nota (Entrada)',
    )
    movement_in_line_ids = fields.One2many(
        'ifdw.dms.automation.move.line',
        'automation_id',
        domain=[('channel_role', '=', 'as_dest')],
        string='Mapeo de Subcarpetas de Entrada (Origen -> Este Modelo)',
        copy=True,
    )

    dest_automation_id = fields.Many2one(
        'ifdw.dms.automation',
        string='Regla Automatización DMS de Destino',
        domain="[('id', '!=', id)]",
        ondelete='set null',
        help='Regla de Automatización DMS hacia la que viajarán los archivos cuando se cree el registro de destino (ej. Archivos de Proyectos o Administración).',
    )
    out_source_root_dir_id = fields.Many2one(
        'dms.directory',
        string='Carpeta Molde Origen (Salida)',
        compute='_compute_effective_movement_roots',
        readonly=True,
    )
    out_dest_root_dir_id = fields.Many2one(
        'dms.directory',
        string='Carpeta Molde Destino (Salida)',
        compute='_compute_effective_movement_roots',
        readonly=True,
    )
    out_dest_model_id = fields.Many2one(
        'ir.model',
        string='Modelo Destino (Salida)',
        compute='_compute_effective_movement_roots',
        readonly=True,
    )
    out_origin_link_field_id = fields.Many2one(
        'ir.model.fields',
        string='Campo de enlace en el Destino (Salida)',
        domain="[('model_id', '=', out_dest_model_id), ('ttype', '=', 'many2one')]",
        ondelete='set null',
        help='Campo del modelo de destino que lo conecta con este modelo de origen.',
    )
    out_after_move_action = fields.Selection(
        selection=[
            ('copy_keep', 'Opción 1: Copiar los archivos al destino manteniendo también los originales en su carpeta de origen.'),
            ('move_delete_dir', 'Opción 2: Mover los archivos al destino y borrar los datos residuales del origen (borra los archivos y carpetas en origen).'),
            ('move_keep_dir', 'Opción 3: Mover los archivos al destino y borrar solo archivos residuales del origen (deja carpetas vacías en origen).'),
        ],
        string='Acción tras trasladar archivos (Salida)',
        default='copy_keep',
        required=True,
    )
    out_post_chatter_summary = fields.Boolean(
        string='Publicar nota de trazabilidad en el Chatter (Salida)',
        default=True,
    )
    out_trace_model_ids = fields.Many2many(
        'ir.model',
        'ifdw_dms_automation_out_trace_model_rel',
        'automation_id',
        'model_id',
        string='Modelos donde publicar nota (Salida)',
    )
    movement_out_line_ids = fields.One2many(
        'ifdw.dms.automation.move.line',
        'automation_id',
        domain=[('channel_role', '=', 'as_source')],
        string='Mapeo de Subcarpetas de Salida (Este Modelo -> Destino)',
        copy=True,
    )

    @api.model
    def _register_hook(self):
        res = super()._register_hook()
        try:
            cat_menu = self.env.ref('dms.menu_dms_category', raise_if_not_found=False)
            auto_menu = self.env.ref('ifdw_dms_automation_workflow.menu_ifdw_dms_automation', raise_if_not_found=False)
            if cat_menu and cat_menu.parent_id and auto_menu and auto_menu.parent_id != cat_menu.parent_id:
                auto_menu.sudo().write({'parent_id': cat_menu.parent_id.id, 'sequence': 12})
        except Exception as e:
            _logger.warning("No se pudo reubicar dinámicamente el menú Automatización DMS: %s", e)
        return res

    @api.constrains('min_image_size_kb', 'filter_small_images')
    def _check_min_image_size_kb(self):
        for rec in self:
            if rec.filter_small_images and not (1 <= rec.min_image_size_kb <= 100):
                raise ValidationError(
                    _('El valor del "Filtro anti-archivos basura chicos" debe estar entre 1 KB y 100 KB (actual: %s KB).')
                    % rec.min_image_size_kb
                )

    def _find_template_root_directory(self, template):
        if not template:
            return self.env['dms.directory']
        template = template.sudo()
        for field_candidate in ('dms_directory_ids', 'directory_ids', 'root_directory_ids'):
            if hasattr(template, field_candidate):
                dirs = getattr(template, field_candidate)
                if dirs:
                    return dirs[0]
        if hasattr(template, 'directory_id') and template.directory_id:
            return template.directory_id

        Directory = self.env['dms.directory'].sudo()
        found = Directory.search([
            ('storage_id', '=', template.storage_id.id),
            ('name', '=', template.name),
        ], limit=1)
        if not found:
            found = Directory.search([
                ('storage_id', '=', template.storage_id.id),
                ('name', 'ilike', template.name),
                ('name', 'not ilike', 'ejemplo'),
            ], limit=1)
        return found

    @api.depends('template_id')
    def _compute_template_info(self):
        for rec in self:
            if rec.template_id:
                t_sudo = rec.template_id.sudo()
                rec.group_ids = t_sudo.group_ids if hasattr(t_sudo, 'group_ids') else False
                rec.template_root_dir_id = rec._find_template_root_directory(t_sudo)
            else:
                rec.group_ids = False
                rec.template_root_dir_id = False

    @api.depends('template_root_dir_id', 'source_automation_id', 'dest_automation_id', 'model_id')
    def _compute_effective_movement_roots(self):
        for rec in self:

            rec.in_source_root_dir_id = rec.source_automation_id.template_root_dir_id if rec.source_automation_id else False
            rec.in_dest_root_dir_id = rec.template_root_dir_id
            rec.in_dest_model_id = rec.model_id

            rec.out_source_root_dir_id = rec.template_root_dir_id
            rec.out_dest_root_dir_id = rec.dest_automation_id.template_root_dir_id if rec.dest_automation_id else False
            rec.out_dest_model_id = rec.dest_automation_id.model_id if rec.dest_automation_id else False

    def _guess_rule_for_subfolder_name(self, folder_name):
        low = (folder_name or '').lower()
        Category = self.env['dms.category'].sudo()
        if 'preventa' in low or 'previo' in low:
            cat = Category.search([('name', 'ilike', 'foto')], limit=1)
            return 'only_inheritance', '', cat.id if cat else False
        if 'foto' in low or 'imagen' in low:
            cat = Category.search([('name', 'ilike', 'foto')], limit=1)
            return 'images', '', cat.id if cat else False
        if 'video' in low or 'vídeo' in low or 'audio' in low:
            cat = Category.search([('name', 'ilike', 'video')], limit=1)
            return 'videos_audios', '', cat.id if cat else False
        if 'plano' in low or 'medicion' in low or 'medición' in low or 'licencia' in low:
            cat = Category.search([('name', 'ilike', 'medicion')], limit=1)
            return 'cad_plans', 'plano, croquis, medicion, licencia, ovp, replanteo', cat.id if cat else False
        if 'presupuesto' in low or 'contrato' in low or 'albaran' in low or 'documento' in low or 'factura' in low:
            cat = Category.search(['|', ('name', 'ilike', 'presupuesto'), ('name', 'ilike', 'documento')], limit=1)
            return 'documents', '', cat.id if cat else False
        cat = Category.search([('name', 'ilike', 'otro')], limit=1)
        return 'catch_all', '', cat.id if cat else False

    @api.onchange('template_id')
    def _onchange_template_id_populate_lines(self):
        if not self.template_id:
            return
        root_dir = self._find_template_root_directory(self.template_id)
        if root_dir and not self.classify_line_ids:
            lines = [(5, 0, 0)]
            for idx, sub in enumerate(root_dir.child_directory_ids.sorted('name'), start=1):
                rule_type, keywords, cat_id = self._guess_rule_for_subfolder_name(sub.name)
                lines.append((0, 0, {
                    'sequence': idx * 10,
                    'template_subdir_id': sub.id,
                    'file_type_rule': rule_type,
                    'filename_keywords': keywords,
                    'category_id': cat_id or (sub.category_id.id if sub.category_id else False),
                }))
            self.classify_line_ids = lines

    def action_reload_template_subfolders(self):
        self.ensure_one()
        root_dir = self.template_root_dir_id
        if not root_dir:
            return
        existing_sub_ids = set(self.classify_line_ids.mapped('template_subdir_id').ids)
        seq = (max(self.classify_line_ids.mapped('sequence') or [0]) + 10)
        for sub in root_dir.child_directory_ids.sorted('name'):
            if sub.id not in existing_sub_ids:
                rule_type, keywords, cat_id = self._guess_rule_for_subfolder_name(sub.name)
                self.env['ifdw.dms.automation.classify.line'].create({
                    'automation_id': self.id,
                    'sequence': seq,
                    'template_subdir_id': sub.id,
                    'file_type_rule': rule_type,
                    'filename_keywords': keywords,
                    'category_id': cat_id or (sub.category_id.id if sub.category_id else False),
                })
                seq += 10

    def _compute_default_trace_models(self, src_rule, dst_rule):
        IrModel = self.env['ir.model'].sudo()
        model_names = set()
        if src_rule and src_rule.model_name:
            model_names.add(src_rule.model_name)
        if dst_rule and dst_rule.model_name:
            model_names.add(dst_rule.model_name)
        if 'crm.lead' in model_names and 'project.project' in model_names:
            model_names.add('sale.order')
        return IrModel.search([('model', 'in', list(model_names))])

    def _find_best_origin_link_field(self, src_rule, dst_rule):
        if not src_rule or not dst_rule or not dst_rule.model_id:
            return self.env['ir.model.fields']
        IrFields = self.env['ir.model.fields'].sudo()
        src_model_name = src_rule.model_name
        dst_model_id = dst_rule.model_id.id
        dst_model_name = dst_rule.model_name

        direct_field = IrFields.search([
            ('model_id', '=', dst_model_id),
            ('ttype', '=', 'many2one'),
            ('relation', '=', src_model_name),
        ], limit=1)
        if direct_field:
            return direct_field
        if dst_model_name == 'project.project':
            return IrFields.search([
                ('model_id', '=', dst_model_id),
                ('name', 'in', ('sale_order_id', 'sale_line_id')),
            ], order='name asc', limit=1)
        return self.env['ir.model.fields']

    @api.onchange('enable_file_movement', 'movement_role', 'source_automation_id', 'dest_automation_id', 'template_id')
    def _onchange_movement_auto_configure(self):
        if not self.enable_file_movement or not self.model_id:
            return

        if self.movement_role == 'as_dest' and self.source_automation_id:
            src_rule = self.source_automation_id
            dst_rule = self
            if not self.origin_link_field_id:
                best_f = self._find_best_origin_link_field(src_rule, dst_rule)
                if best_f:
                    self.origin_link_field_id = best_f.id
            if not self.trace_model_ids:
                self.trace_model_ids = [(6, 0, self._compute_default_trace_models(src_rule, dst_rule).ids)]
            src_root = src_rule.template_root_dir_id
            dst_root = dst_rule.template_root_dir_id
            if src_root and dst_root and not self.movement_in_line_ids:
                dst_subs = dst_root.child_directory_ids.sorted('name')
                move_lines = [(5, 0, 0)]
                for idx, s_sub in enumerate(src_root.child_directory_ids.sorted('name'), start=1):
                    matched_dst = self._match_existing_dest_subfolder(s_sub, dst_subs)
                    if matched_dst:
                        move_lines.append((0, 0, {
                            'sequence': idx * 10,
                            'channel_role': 'as_dest',
                            'source_subdir_id': s_sub.id,
                            'dest_subdir_id': matched_dst.id,
                        }))
                self.movement_in_line_ids = move_lines

        elif self.movement_role == 'as_source' and self.dest_automation_id:
            src_rule = self
            dst_rule = self.dest_automation_id
            if not self.out_origin_link_field_id:
                best_f = self._find_best_origin_link_field(src_rule, dst_rule)
                if best_f:
                    self.out_origin_link_field_id = best_f.id
            if not self.out_trace_model_ids:
                self.out_trace_model_ids = [(6, 0, self._compute_default_trace_models(src_rule, dst_rule).ids)]
            src_root = src_rule.template_root_dir_id
            dst_root = dst_rule.template_root_dir_id
            if src_root and dst_root and not self.movement_out_line_ids:
                dst_subs = dst_root.child_directory_ids.sorted('name')
                move_lines = [(5, 0, 0)]
                for idx, s_sub in enumerate(src_root.child_directory_ids.sorted('name'), start=1):
                    matched_dst = self._match_existing_dest_subfolder(s_sub, dst_subs)
                    if matched_dst:
                        move_lines.append((0, 0, {
                            'sequence': idx * 10,
                            'channel_role': 'as_source',
                            'source_subdir_id': s_sub.id,
                            'dest_subdir_id': matched_dst.id,
                        }))
                self.movement_out_line_ids = move_lines

    def _match_existing_dest_subfolder(self, src_sub, dst_subs):
        s_low = (src_sub.name or '').lower()
        for d_sub in dst_subs:
            d_low = (d_sub.name or '').lower()
            if ('foto' in s_low and ('preventa' in d_low or 'previo' in d_low or 'inicial' in d_low)):
                return d_sub
            if ('video' in s_low or 'vídeo' in s_low) and ('video' in d_low or 'vídeo' in d_low):
                return d_sub
            if ('plano' in s_low or 'medicion' in s_low) and ('plano' in d_low or 'medicion' in d_low):
                return d_sub
            if ('presupuesto' in s_low) and ('presupuesto' in d_low):
                return d_sub
            if ('otro' in s_low or '99' in s_low) and ('otro' in d_low or '99' in d_low):
                return d_sub
        return dst_subs[:1]

    def _sync_bidirectional_movement_mirror(self):

        if self.env.context.get('skip_ifdw_mirror_sync'):
            return
        ctx = dict(self.env.context, skip_ifdw_mirror_sync=True)
        MoveLine = self.env['ifdw.dms.automation.move.line'].sudo().with_context(ctx)

        for rec in self:
            if not rec.enable_file_movement:
                continue

            if rec.movement_role == 'as_source' and rec.dest_automation_id:
                partner_dst = rec.dest_automation_id.sudo().with_context(ctx)
                trace_ids = rec.out_trace_model_ids.ids or rec._compute_default_trace_models(rec, partner_dst).ids
                if not rec.out_trace_model_ids and trace_ids:
                    rec.with_context(ctx).write({'out_trace_model_ids': [(6, 0, trace_ids)]})

                MoveLine.search([
                    ('automation_id', '=', partner_dst.id),
                    ('channel_role', '=', 'as_dest'),
                ]).unlink()
                in_lines_vals = []
                for line in rec.movement_out_line_ids.sorted('sequence'):
                    in_lines_vals.append((0, 0, {
                        'sequence': line.sequence,
                        'channel_role': 'as_dest',
                        'source_subdir_id': line.source_subdir_id.id,
                        'dest_subdir_id': line.dest_subdir_id.id,
                    }))

                partner_vals = {
                    'enable_file_movement': True,
                    'source_automation_id': rec.id,
                    'origin_link_field_id': rec.out_origin_link_field_id.id,
                    'after_move_action': rec.out_after_move_action,
                    'post_chatter_summary': rec.out_post_chatter_summary,
                    'trace_model_ids': [(6, 0, trace_ids)],
                    'movement_in_line_ids': in_lines_vals,
                }
                if not partner_dst.dest_automation_id:
                    partner_vals['movement_role'] = 'as_dest'
                partner_dst.write(partner_vals)

            elif rec.movement_role == 'as_dest' and rec.source_automation_id:
                partner_src = rec.source_automation_id.sudo().with_context(ctx)
                trace_ids = rec.trace_model_ids.ids or rec._compute_default_trace_models(partner_src, rec).ids
                if not rec.trace_model_ids and trace_ids:
                    rec.with_context(ctx).write({'trace_model_ids': [(6, 0, trace_ids)]})

                MoveLine.search([
                    ('automation_id', '=', partner_src.id),
                    ('channel_role', '=', 'as_source'),
                ]).unlink()
                out_lines_vals = []
                for line in rec.movement_in_line_ids.sorted('sequence'):
                    out_lines_vals.append((0, 0, {
                        'sequence': line.sequence,
                        'channel_role': 'as_source',
                        'source_subdir_id': line.source_subdir_id.id,
                        'dest_subdir_id': line.dest_subdir_id.id,
                    }))

                partner_vals = {
                    'enable_file_movement': True,
                    'dest_automation_id': rec.id,
                    'out_origin_link_field_id': rec.origin_link_field_id.id,
                    'out_after_move_action': rec.after_move_action,
                    'out_post_chatter_summary': rec.post_chatter_summary,
                    'out_trace_model_ids': [(6, 0, trace_ids)],
                    'movement_out_line_ids': out_lines_vals,
                }
                if not partner_src.source_automation_id:
                    partner_vals['movement_role'] = 'as_source'
                partner_src.write(partner_vals)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_bidirectional_movement_mirror()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_bidirectional_movement_mirror()
        return res

    def action_dummy_preview_smart_button(self):
        return False

    def _record_matches_domain(self, record):
        self.ensure_one()
        if not self.filter_domain or self.filter_domain.strip() in ('', '[]'):
            return True
        try:
            domain = safe_eval(self.filter_domain)
            if not isinstance(domain, list):
                return True
            matched = record.sudo().filtered_domain(domain)
            return bool(matched)
        except Exception as e:
            _logger.warning("Error evaluando filter_domain en regla %s: %s", self.name, e)
            return True

    def _format_cloned_root_name(self, record):
        self.ensure_one()
        rec_name = getattr(record, 'display_name', False) or getattr(record, 'name', False) or f"ID-{record.id}"
        return re.sub(r'[\\/:*?"<>|\r\n\t]+', '-', str(rec_name)).strip()

    def _clone_template_for_record(self, record):
        self.ensure_one()
        Directory = self.env['dms.directory'].sudo()
        root_molde = self.template_root_dir_id
        if not root_molde:
            return Directory

        target_name = self._format_cloned_root_name(record)
        storage = self.storage_id.sudo()
        parent_dir = self.parent_directory_id.sudo() if self.parent_directory_id else self.template_id.sudo().parent_directory_id

        # Primero busco si ya existe la carpeta (dentro de Carpeta Padre si la hay, o en la raíz si no la hay)
        search_domain = [
            ('storage_id', '=', storage.id),
            ('name', '=', target_name),
            ('id', '!=', root_molde.id),
        ]
        if parent_dir:
            search_domain.append(('parent_id', '=', parent_dir.id))
        else:
            search_domain.append(('is_root_directory', '=', True))

        existing = Directory.search(search_domain, limit=1)
        if existing:
            return existing

        # Segundo preparar valores de la carpeta principal del registro
        root_vals = {
            'name': target_name,
            'storage_id': storage.id,
            'category_id': root_molde.category_id.id if root_molde.category_id else False,
            'tag_ids': [(6, 0, root_molde.tag_ids.ids)],
        }
        if 'res_model' in Directory._fields:
            root_vals['res_model'] = record._name
        if 'res_id' in Directory._fields:
            root_vals['res_id'] = record.id

        if parent_dir:
            # Nace DENTRO de la Carpeta Padre (Proyectos, Ventas, Administración) heredando sus permisos
            root_vals.update({
                'is_root_directory': False,
                'parent_id': parent_dir.id,
                'inherit_group_ids': True,
            })
        else:
            # Solo si la plantilla NO tiene Carpeta Padre, nace en la raíz con los grupos de la plantilla
            access_group_ids = self.group_ids.sudo().ids
            root_vals.update({
                'is_root_directory': True,
                'group_ids': [(6, 0, access_group_ids)],
            })

        new_root = Directory.create(root_vals)

        # Tercero clonar las subcarpetas respetando la herencia limpia (o excepciones si alguna no hereda)
        for sub in root_molde.child_directory_ids.sorted('name'):
            sub_inherit = sub.inherit_group_ids if 'inherit_group_ids' in Directory._fields else True
            sub_vals = {
                'name': sub.name,
                'is_root_directory': False,
                'parent_id': new_root.id,
                'storage_id': storage.id,
                'inherit_group_ids': sub_inherit,
                'category_id': sub.category_id.id if sub.category_id else False,
                'tag_ids': [(6, 0, sub.tag_ids.ids)],
            }
            if not sub_inherit and sub.group_ids:
                sub_vals['group_ids'] = [(6, 0, sub.group_ids.ids)]

            Directory.create(sub_vals)

        return new_root


    def _get_effective_dest_rule_and_source_rule(self):
        self.ensure_one()
        if not self.enable_file_movement:
            return (False, False)
        if self.source_automation_id:
            return (self.source_automation_id, self)
        mirror_src = self.env['ifdw.dms.automation'].sudo().search([
            ('active', '=', True),
            ('enable_file_movement', '=', True),
            ('dest_automation_id', '=', self.id),
        ], limit=1)
        if mirror_src:
            return (mirror_src, self)
        return (False, False)

    def _resolve_chain_records_for_movement(self, dest_record):
        self.ensure_one()
        src_rule, dst_rule = self._get_effective_dest_rule_and_source_rule()
        if not src_rule or not dst_rule:
            return (False, False)

        src_model = src_rule.model_name
        dest_sudo = dest_record.sudo()
        bridge_order = False
        origin_record = False

        link_field = dst_rule.origin_link_field_id or src_rule.out_origin_link_field_id
        if link_field and hasattr(dest_sudo, link_field.name):
            linked_val = getattr(dest_sudo, link_field.name)
            if linked_val:
                if linked_val._name == src_model:
                    origin_record = linked_val
                elif linked_val._name == 'sale.order':
                    bridge_order = linked_val
                    if src_model == 'crm.lead' and getattr(linked_val, 'opportunity_id', False):
                        origin_record = linked_val.opportunity_id
                elif linked_val._name == 'sale.order.line' and getattr(linked_val, 'order_id', False):
                    bridge_order = linked_val.order_id
                    if src_model == 'sale.order':
                        origin_record = bridge_order
                    elif src_model == 'crm.lead' and getattr(bridge_order, 'opportunity_id', False):
                        origin_record = bridge_order.opportunity_id

        if not origin_record and dest_sudo._name == 'project.project':
            order = getattr(dest_sudo, 'sale_order_id', False) or (
                dest_sudo.sale_line_id.order_id if getattr(dest_sudo, 'sale_line_id', False) else False
            )
            if order:
                bridge_order = order
                if src_model == 'sale.order':
                    origin_record = order
                elif src_model == 'crm.lead' and getattr(order, 'opportunity_id', False):
                    origin_record = order.opportunity_id

        return (origin_record, bridge_order)

    def _is_dms_file_locked(self, dms_file):
        return bool(getattr(dms_file, 'is_locked', False) or getattr(dms_file, 'locked_by', False))

    def _execute_file_movement_from_origin(self, dest_record, dest_root_dir):
        self.ensure_one()
        src_rule, dst_rule = self._get_effective_dest_rule_and_source_rule()
        if not src_rule or not dst_rule or not dest_root_dir:
            return False

        move_lines = dst_rule.movement_in_line_ids or src_rule.movement_out_line_ids
        after_action = dst_rule.after_move_action or src_rule.out_after_move_action or 'copy_keep'
        post_summary = dst_rule.post_chatter_summary if dst_rule.movement_in_line_ids else src_rule.out_post_chatter_summary
        trace_models = dst_rule.trace_model_ids or src_rule.out_trace_model_ids or self._compute_default_trace_models(src_rule, dst_rule)

        origin_record, bridge_order = dst_rule._resolve_chain_records_for_movement(dest_record)
        if not origin_record or not hasattr(origin_record, 'dms_directory_id') or not origin_record.dms_directory_id:
            return False

        crm_policy = 'global_rule'
        if origin_record._name == 'crm.lead' and hasattr(origin_record, 'ifdw_project_transfer_policy'):
            crm_policy = origin_record.ifdw_project_transfer_policy or 'global_rule'
        if crm_policy == 'no_transfer':
            return False

        origin_root_dir = origin_record.dms_directory_id.sudo()
        if not origin_root_dir.exists() or origin_root_dir == dest_root_dir:
            return False

        DmsFile = self.env['dms.file'].sudo()
        moved_or_copied_count = 0
        attachments_to_clean = self.env['ir.attachment'].sudo()
        has_locked_files_in_origin = False

        origin_subs_by_name = {sub.name: sub for sub in origin_root_dir.child_directory_ids}
        dest_subs_by_name = {sub.name: sub for sub in dest_root_dir.child_directory_ids}

        for move_line in move_lines:
            src_sub_name = move_line.source_subdir_id.name
            dst_sub_name = move_line.dest_subdir_id.name
            real_src_sub = origin_subs_by_name.get(src_sub_name)
            real_dst_sub = dest_subs_by_name.get(dst_sub_name)
            if not real_src_sub or not real_dst_sub:
                continue

            for dms_file in list(real_src_sub.file_ids):
                if (
                    crm_policy == 'only_new'
                    and dest_record._name == 'project.project'
                    and dms_file.ifdw_transferred_project_ids
                    and dest_record.id not in dms_file.ifdw_transferred_project_ids.ids
                ):
                    continue

                is_locked = self._is_dms_file_locked(dms_file)
                if is_locked:
                    has_locked_files_in_origin = True

                already_in_dest = DmsFile.with_context(ifdw_disable_child_of_directory=True).search([
                    ('directory_id', '=', real_dst_sub.id),
                    ('name', '=', dms_file.name),
                ], limit=1)

                if already_in_dest:
                    if dest_record._name == 'project.project':
                        dms_file.write({'ifdw_transferred_project_ids': [(4, dest_record.id)]})
                    if after_action in ('move_delete_dir', 'move_keep_dir') and not is_locked:
                        if dms_file.ifdw_source_attachment_id:
                            attachments_to_clean |= dms_file.ifdw_source_attachment_id
                        dms_file.with_context(skip_ifdw_attachment_sync=True).unlink()
                    continue

                if after_action == 'copy_keep' or is_locked:
                    new_f = DmsFile.create({
                        'name': dms_file.name,
                        'directory_id': real_dst_sub.id,
                        'content': dms_file.content,
                        'category_id': dms_file.category_id.id if dms_file.category_id else False,
                        'tag_ids': [(6, 0, dms_file.tag_ids.ids)],
                        'ifdw_source_attachment_id': False,
                        'ifdw_origin_lead_id': origin_record.id if origin_record._name == 'crm.lead' else False,
                    })
                    if dest_record._name == 'project.project':
                        dms_file.write({'ifdw_transferred_project_ids': [(4, dest_record.id)]})
                        new_f.write({'ifdw_transferred_project_ids': [(4, dest_record.id)]})
                else:
                    if dms_file.ifdw_source_attachment_id:
                        attachments_to_clean |= dms_file.ifdw_source_attachment_id
                    write_vals = {
                        'directory_id': real_dst_sub.id,
                        'ifdw_source_attachment_id': False,
                    }
                    if dest_record._name == 'project.project':
                        write_vals['ifdw_transferred_project_ids'] = [(4, dest_record.id)]
                    dms_file.write(write_vals)

                moved_or_copied_count += 1

        if after_action in ('move_delete_dir', 'move_keep_dir'):
            extra_origin_atts = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', origin_record._name),
                ('res_id', '=', origin_record.id),
                ('x_ifdw_dms_synced', '=', True),
            ])

            locked_att_ids = set(
                DmsFile.with_context(ifdw_disable_child_of_directory=True).search([
                    ('directory_id', 'child_of', origin_root_dir.id),
                    ('is_locked', '=', True),
                ]).mapped('ifdw_source_attachment_id').ids
            )
            all_atts_to_delete = (attachments_to_clean | extra_origin_atts).exists().filtered(
                lambda a: a.id not in locked_att_ids
            )
            if all_atts_to_delete:
                try:
                    all_atts_to_delete.with_context(skip_ifdw_dms_unlink_sync=True).unlink()
                except Exception as e:
                    _logger.warning("Aviso al limpiar adjuntos residuales del Chatter en origen %s: %s", origin_record.display_name, e)

        if after_action == 'move_delete_dir' and not has_locked_files_in_origin:
            try:
                origin_record.sudo().write({'dms_directory_id': False})
                origin_root_dir.with_context(skip_ifdw_attachment_sync=True).unlink()
            except Exception as e:
                _logger.warning("No se pudo eliminar carpeta de origen %s tras mover: %s", origin_root_dir.name, e)

        if origin_record._name == 'crm.lead':
            action_selection_dict = dict(self._fields['after_move_action'].selection)
            policy_selection_dict = dict(origin_record._fields['ifdw_project_transfer_policy'].selection)
            self.env['ifdw.dms.crm.transfer.log'].sudo().create({
                'lead_id': origin_record.id,
                'project_id': dest_record.id if dest_record._name == 'project.project' else False,
                'sale_order_id': bridge_order.id if bridge_order else False,
                'files_count': moved_or_copied_count,
                'operation_mode': action_selection_dict.get(after_action, after_action),
                'crm_policy_used': policy_selection_dict.get(crm_policy, crm_policy),
            })

        if post_summary:
            action_selection_dict = dict(self._fields['after_move_action'].selection)
            action_label = action_selection_dict.get(after_action, after_action)
            allowed_model_names = set(trace_models.mapped('model'))

            body = Markup(
                "<div class='o_mail_notification'>"
                "<strong>Automatización DMS: Traspaso Documental Completado</strong><br/>"
                "<ul>"
                "<li><strong>Flujo aplicado:</strong> %s -&gt; %s</li>"
                "<li><strong>Registro origen:</strong> %s</li>"
                "<li><strong>Registro destino:</strong> %s (%s)</li>"
                "<li><strong>Acción ejecutada:</strong> %s</li>"
                "<li><strong>Archivos procesados:</strong> %s archivo(s)</li>"
                "</ul>"
                "</div>"
            ) % (
                escape(src_rule.name),
                escape(dst_rule.name),
                escape(origin_record.display_name),
                escape(dest_record.display_name),
                escape(dest_root_dir.storage_id.name),
                escape(action_label),
                moved_or_copied_count,
            )

            candidate_records = [origin_record, bridge_order, dest_record]
            posted_keys = set()
            for target_rec in candidate_records:
                if not target_rec or not target_rec.exists():
                    continue
                key = (target_rec._name, target_rec.id)
                if key in posted_keys or target_rec._name not in allowed_model_names:
                    continue
                if hasattr(target_rec, 'message_post'):
                    try:
                        target_rec.sudo().message_post(body=body, subtype_xmlid='mail.mt_note')
                        posted_keys.add(key)
                    except Exception as e:
                        _logger.warning("No se pudo publicar nota de trazabilidad DMS en %s: %s", target_rec.display_name, e)

        return True

    def _build_formatted_filename(self, attachment, origin_label, root_dir=None):
        self.ensure_one()
        orig_name = attachment.name or 'archivo'
        base_name, ext_dot = os.path.splitext(orig_name)

        if not self.auto_rename_chatter or self.rename_format == 'fmt_0_orig':
            final_base = base_name
        elif self.rename_format == 'fmt_0_seq':
            seq_num = 1
            if root_dir:
                existing_count = self.env['dms.file'].sudo().with_context(
                    ifdw_disable_child_of_directory=True
                ).search_count([('directory_id', 'child_of', root_dir.id)])
                seq_num = existing_count + 1
            final_base = f"{seq_num:03d}-{base_name}"
        else:
            dt_local = fields.Datetime.context_timestamp(self, attachment.create_date or fields.Datetime.now())
            clean_origin = re.sub(r'[\\/:*?"<>|\r\n\t]+', '-', str(origin_label or 'Doc').strip())
            clean_origin = re.sub(r'\s+', '-', clean_origin)[:28].strip('_-') or 'Doc'
            user_name = re.sub(r'\s+', '-', (attachment.create_uid.name or 'Usuario').strip())[:20]

            if self.rename_format == 'fmt_1':
                final_base = f"{dt_local.strftime('%Y%m%d-%H%M')}_{clean_origin}_{base_name}"
            elif self.rename_format == 'fmt_2':
                final_base = f"{dt_local.strftime('%y-%m-%d')}_{clean_origin}_{base_name}"
            elif self.rename_format == 'fmt_3':
                final_base = f"{base_name}_{clean_origin}_{dt_local.strftime('%y-%m-%d')}"
            elif self.rename_format == 'fmt_4':
                final_base = f"{clean_origin}_{dt_local.strftime('%y-%m-%d')}_{base_name}"
            elif self.rename_format == 'fmt_5':
                final_base = f"{dt_local.strftime('%y-%m-%d')}_{user_name}_{clean_origin}_{base_name}"
            else:
                final_base = base_name

        if len(final_base) > MAX_LINUX_BASE_FILENAME_CHARS:
            final_base = final_base[:MAX_LINUX_BASE_FILENAME_CHARS].rstrip('_- ')

        return f"{final_base}{ext_dot}"

    def _classify_attachment_into_record_folder(self, attachment, main_record, origin_label, tag_name=False, forced_template_subdir=False):
        self.ensure_one()
        if not attachment.datas:
            return False

        fname_low = (attachment.name or '').lower()
        ext_low = os.path.splitext(fname_low)[1].lstrip('.').lower()
        mimetype_low = (attachment.mimetype or '').lower()

        is_cad_or_svg = (
            ext_low in CAD_EXTENSIONS
            or ext_low == 'svg'
            or 'svg' in mimetype_low
            or 'dwg' in mimetype_low
            or 'dxf' in mimetype_low
            or 'dwf' in mimetype_low
        )
        if self.filter_small_images and not is_cad_or_svg:
            for pat in SIGNATURE_NAME_PATTERNS:
                if pat in fname_low:
                    return False
            if mimetype_low.startswith('image/'):
                min_bytes = (self.min_image_size_kb or 30) * 1024
                if 0 < (attachment.file_size or 0) < min_bytes:
                    return False

        if not hasattr(main_record, '_ensure_dms_directory_by_rule'):
            return False
        root_dir = main_record._ensure_dms_directory_by_rule(self)
        if not root_dir:
            return False

        matched_line = False
        target_sub_name = False
        target_category_id = False

        if forced_template_subdir:
            target_sub_name = forced_template_subdir.name
            target_category_id = forced_template_subdir.category_id.id if forced_template_subdir.category_id else False
        else:
            active_lines = self.classify_line_ids.sorted('sequence').filtered(
                lambda l: l.file_type_rule != 'only_inheritance'
            )
            catch_all_line = active_lines.filtered(lambda l: l.file_type_rule == 'catch_all')[:1]
            specific_lines = active_lines.filtered(
                lambda l: l.file_type_rule == 'cad_plans' or bool(l.filename_keywords) or bool(l.custom_extensions)
            )
            general_lines = active_lines.filtered(
                lambda l: l.file_type_rule != 'catch_all' and l not in specific_lines
            )

            for line in (specific_lines + general_lines):
                if line._matches_attachment(attachment):
                    matched_line = line
                    break

            if not matched_line:
                matched_line = catch_all_line
            if matched_line:
                target_sub_name = matched_line.template_subdir_id.name
                target_category_id = matched_line.category_id.id if matched_line.category_id else False

        if not target_sub_name:
            return False

        target_dir = root_dir.child_directory_ids.filtered(lambda d: d.name == target_sub_name)[:1]
        if not target_dir:
            target_dir = self.env['dms.directory'].sudo().create({
                'name': target_sub_name,
                'is_root_directory': False,
                'parent_id': root_dir.id,
                'storage_id': root_dir.storage_id.id,
                'inherit_group_ids': True,
                'category_id': target_category_id,
            })

        DmsFile = self.env['dms.file'].sudo()
        final_name = self._build_formatted_filename(attachment, origin_label, root_dir=root_dir)

        existing = DmsFile.with_context(ifdw_disable_child_of_directory=True).search([
            ('directory_id', '=', target_dir.id),
            '|', ('name', '=', final_name), ('name', '=', attachment.name),
        ], limit=1)
        if existing:
            return False

        file_vals = {
            'name': final_name,
            'directory_id': target_dir.id,
            'content': attachment.datas,
            'ifdw_source_attachment_id': attachment.id,
            'ifdw_origin_lead_id': main_record.id if main_record._name == 'crm.lead' else False,
        }
        if target_category_id:
            file_vals['category_id'] = target_category_id

        if tag_name:
            Tag = self.env['dms.tag'].sudo()
            clean_tag = str(tag_name).strip()[:50]
            tag = Tag.search([('name', '=', clean_tag)], limit=1)
            if not tag:
                tag = Tag.create({'name': clean_tag})
            file_vals['tag_ids'] = [(4, tag.id)]

        dms_file = DmsFile.create(file_vals)
        attachment.sudo().with_context(skip_ifdw_attachment_hook=True).write({'x_ifdw_dms_synced': True})

        return {
            'dms_file': dms_file,
            'original_name': attachment.name or 'archivo',
            'dms_name': dms_file.name,
            'dest_folder_name': target_dir.name,
            'user_name': (attachment.create_uid.name if attachment.create_uid else False) or self.env.user.name,
        }
