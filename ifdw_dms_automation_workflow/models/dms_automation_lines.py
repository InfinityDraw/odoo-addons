# -*- coding: utf-8 -*-
# Copyright 2026 Infinity Draw (https://infinitydraw.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import os
import unicodedata
from odoo import api, fields, models
from .dms_automation import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    CAD_EXTENSIONS,
    DOC_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
)


def _normalize_no_accents(text):
    """Convierte a minúsculas y elimina tildes/diacríticos (ej. 'Prevención' -> 'prevencion')."""
    if not text:
        return ''
    nfkd = unicodedata.normalize('NFKD', str(text).lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


class IfdwDmsAutomationClassifyLine(models.Model):
    _name = 'ifdw.dms.automation.classify.line'
    _description = 'Línea de Regla Chatter Auto-clasificación'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Orden',
        default=10,
        help='Orden de prioridad con el que se evalúa esta regla.',
    )
    automation_id = fields.Many2one(
        'ifdw.dms.automation',
        string='Regla de Automatización',
        required=True,
        ondelete='cascade',
    )
    template_root_dir_id = fields.Many2one(
        'dms.directory',
        related='automation_id.template_root_dir_id',
        readonly=True,
    )
    template_subdir_id = fields.Many2one(
        'dms.directory',
        string='Subcarpeta de la Plantilla',
        required=True,
        domain="[('parent_id', '=', template_root_dir_id)]",
        ondelete='cascade',
        help='Elige a qué subcarpeta de tu Plantilla DMS embebida irán a parar los archivos que cumplan esta fila.',
    )
    file_type_rule = fields.Selection(
        selection=[
            ('images', 'Fotografías e Imágenes (JPG, PNG, HEIC, HEIF, AVIF, WEBP, DNG, RAW...)'),
            ('docs_and_images', 'Documentos e Imágenes (PDF, Word, Excel, JPG, PNG, HEIC, WEBP...)'),
            ('videos_audios', 'Vídeos y Notas de Voz / Audios (MP4, MOV, WEBM, OGG, OPUS, MP3, M4A...)'),
            ('only_videos', 'Solo Vídeos (MP4, MOV, AVI, MKV, WEBM, 3GP...)'),
            ('only_audios', 'Solo Audios / Notas de Voz (OGG, OPUS, M4A, MP3, WAV...)'),
            ('cad_plans', 'Planos CAD/BIM/Mediciones (DWG, DXF, DWF, IFC, BC3) + PDF con palabras clave'),
            ('documents', 'Documentos Ofimáticos y PDF Estándar (PDF, DOC, DOCX, XLS, XLSX, ODT, ODS...)'),
            ('archives', 'Archivos Comprimidos (ZIP, RAR, 7Z, TAR, GZ)'),
            ('catch_all', 'Resto de Archivos / Cajón de Sastre (Catch-All: SVG, ZIP y cualquier formato no tipificado)'),
            ('only_inheritance', 'Solo Herencia / Movimiento (No recibe archivos directos del Chatter)'),
        ],
        string='Tipo de Archivo a Clasificar',
        required=True,
        default='images',
        help='Selecciona la familia de archivos que se guardará automáticamente en esta subcarpeta cuando se suban por el clip del Chatter.',
    )
    filename_keywords = fields.Char(
        string='Palabras clave en nombre (Opcional)',
        help='Palabras separadas por comas sin importar mayúsculas ni tildes (ej. "contrato, prevencion, banco, titulo"). Las filas con palabras clave tienen prioridad sobre las genéricas.',
    )
    custom_extensions = fields.Char(
        string='Extensiones extra (Opcional)',
        help='Extensiones adicionales separadas por comas sin el punto (ej. "bc3, plt, rvt").',
    )
    category_id = fields.Many2one(
        'dms.category',
        string='Categoría DMS a aplicar',
        ondelete='set null',
        help='Categoría de Documentos > Configuración > Organizar > Categorías que se asignará automáticamente al archivo clasificado.',
    )

    def _is_bitmap_image(self, ext, mimetype):
        if (
            ext in CAD_EXTENSIONS
            or ext == 'svg'
            or 'svg' in mimetype
            or 'dwg' in mimetype
            or 'dxf' in mimetype
            or 'dwf' in mimetype
        ):
            return False
        return mimetype.startswith('image/') or ext in IMAGE_EXTENSIONS

    def _is_office_or_pdf(self, ext, mimetype):
        return (
            mimetype == 'application/pdf'
            or ext in DOC_EXTENSIONS
            or 'word' in mimetype
            or 'excel' in mimetype
            or 'spreadsheet' in mimetype
            or 'opendocument' in mimetype
        )

    def _matches_attachment(self, attachment):
        self.ensure_one()
        raw_fname = attachment.name or ''
        fname_norm = _normalize_no_accents(raw_fname)
        ext = os.path.splitext(raw_fname)[1].lstrip('.').lower()
        mimetype = (attachment.mimetype or '').lower()

        extra_exts = {e.strip().lstrip('.').lower() for e in (self.custom_extensions or '').split(',') if e.strip()}
        keywords = [_normalize_no_accents(k.strip()) for k in (self.filename_keywords or '').split(',') if k.strip()]

        if self.file_type_rule == 'cad_plans':
            if (
                ext in CAD_EXTENSIONS
                or ext in extra_exts
                or 'dwg' in mimetype
                or 'dxf' in mimetype
                or 'dwf' in mimetype
                or mimetype == 'application/acad'
            ):
                return True
            if ext == 'pdf' and keywords and any(kw in fname_norm for kw in keywords):
                return True
            return False

        if keywords and not any(kw in fname_norm for kw in keywords):
            return False

        if ext in extra_exts:
            return True

        if self.file_type_rule == 'images':
            return self._is_bitmap_image(ext, mimetype)

        if self.file_type_rule == 'docs_and_images':
            return self._is_bitmap_image(ext, mimetype) or self._is_office_or_pdf(ext, mimetype)

        if self.file_type_rule == 'videos_audios':
            return mimetype.startswith('video/') or mimetype.startswith('audio/') or ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS
        if self.file_type_rule == 'only_videos':
            return mimetype.startswith('video/') or ext in VIDEO_EXTENSIONS
        if self.file_type_rule == 'only_audios':
            return mimetype.startswith('audio/') or ext in AUDIO_EXTENSIONS
        if self.file_type_rule == 'documents':
            return self._is_office_or_pdf(ext, mimetype)
        if self.file_type_rule == 'archives':
            return ext in ARCHIVE_EXTENSIONS or 'zip' in mimetype or 'compressed' in mimetype
        return False


class IfdwDmsAutomationSatelliteLine(models.Model):
    _name = 'ifdw.dms.automation.satellite.line'
    _description = 'Línea de Modelo Satélite Auto-clasificación (Pestaña 2)'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    automation_id = fields.Many2one(
        'ifdw.dms.automation',
        string='Regla de Automatización',
        required=True,
        ondelete='cascade',
    )
    parent_model_id = fields.Many2one('ir.model', related='automation_id.model_id', readonly=True)
    parent_model_name = fields.Char(related='automation_id.model_name', readonly=True)
    template_root_dir_id = fields.Many2one('dms.directory', related='automation_id.template_root_dir_id', readonly=True)
    satellite_model_id = fields.Many2one(
        'ir.model',
        string='Modelo Extra (Satélite)',
        required=True,
        domain="[('is_mail_thread', '=', True), ('transient', '=', False)]",
        ondelete='cascade',
        help='Modelo secundario con Chatter (ej. Tarea, Contrato, Pedido de Venta o Factura) cuyos archivos subidos al Chatter irán a la carpeta del modelo principal.',
    )
    link_field_id = fields.Many2one(
        'ir.model.fields',
        string='Campo que lo une al Modelo de plantilla',
        required=True,
        domain="[('model_id', '=', satellite_model_id), ('ttype', '=', 'many2one')]",
        ondelete='cascade',
        help='Campo relacional dentro del Modelo Extra que apunta al registro principal (se rellena automáticamente al elegir el modelo extra).',
    )
    force_subdir_id = fields.Many2one(
        'dms.directory',
        string='Forzar Subcarpeta (Opcional)',
        domain="[('parent_id', '=', template_root_dir_id)]",
        ondelete='set null',
        help='Si lo dejas en blanco, los archivos se clasifican según la Pestaña 1. Si eliges una subcarpeta aquí, todos irán a ella.',
    )
    auto_tag_record_name = fields.Boolean(
        string='Etiquetar con nombre del registro',
        default=True,
        help='Añade automáticamente al archivo en el DMS una etiqueta con el nombre del registro satélite (ej. el nombre de la Tarea).',
    )

    @api.onchange('satellite_model_id')
    def _onchange_satellite_model_id_auto_field(self):
        if not self.satellite_model_id or not self.parent_model_name:
            return
        direct = self.env['ir.model.fields'].sudo().search([
            ('model_id', '=', self.satellite_model_id.id),
            ('ttype', '=', 'many2one'),
            ('relation', '=', self.parent_model_name),
        ], limit=1)
        if direct:
            self.link_field_id = direct.id


class IfdwDmsAutomationMoveLine(models.Model):
    _name = 'ifdw.dms.automation.move.line'
    _description = 'Línea de Movimiento de Archivos entre Subcarpetas (Pestaña 3)'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    automation_id = fields.Many2one(
        'ifdw.dms.automation',
        string='Regla de Automatización',
        required=True,
        ondelete='cascade',
    )
    channel_role = fields.Selection(
        selection=[
            ('as_dest', 'Canal de Entrada (Recibir de Origen)'),
            ('as_source', 'Canal de Salida (Enviar a Destino)'),
        ],
        string='Canal de Movimiento',
        default='as_dest',
        required=True,
    )
    source_root_dir_id = fields.Many2one(
        'dms.directory',
        compute='_compute_line_root_dirs',
        readonly=True,
    )
    dest_root_dir_id = fields.Many2one(
        'dms.directory',
        compute='_compute_line_root_dirs',
        readonly=True,
    )
    source_subdir_id = fields.Many2one(
        'dms.directory',
        string='Subcarpeta Origen (Existente)',
        required=True,
        domain="[('parent_id', '=', source_root_dir_id)]",
        ondelete='cascade',
        help='Subcarpeta ya existente en la Plantilla DMS embebida de origen.',
    )
    dest_subdir_id = fields.Many2one(
        'dms.directory',
        string='Subcarpeta Destino (Existente)',
        required=True,
        domain="[('parent_id', '=', dest_root_dir_id)]",
        ondelete='cascade',
        help='Subcarpeta ya existente en la Plantilla DMS embebida de destino.',
    )

    @api.depends(
        'channel_role',
        'automation_id.in_source_root_dir_id',
        'automation_id.in_dest_root_dir_id',
        'automation_id.out_source_root_dir_id',
        'automation_id.out_dest_root_dir_id',
    )
    def _compute_line_root_dirs(self):
        for rec in self:
            auto = rec.automation_id
            if not auto:
                rec.source_root_dir_id = False
                rec.dest_root_dir_id = False
            elif rec.channel_role == 'as_source':
                rec.source_root_dir_id = auto.out_source_root_dir_id
                rec.dest_root_dir_id = auto.out_dest_root_dir_id
            else:
                rec.source_root_dir_id = auto.in_source_root_dir_id
                rec.dest_root_dir_id = auto.in_dest_root_dir_id
