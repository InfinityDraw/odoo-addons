# -*- coding: utf-8 -*-
# Copyright 2026 Infinity Draw (https://infinitydraw.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from collections import defaultdict
import logging
from markupsafe import Markup, escape
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class DmsFilePlavifomExtension(models.Model):
    _inherit = 'dms.file'

    ifdw_source_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Adjunto Origen Chatter',
        ondelete='set null',
        index=True,
        copy=False,
        help='Vincula este archivo DMS con el adjunto original subido al Chatter para sincronizar su ciclo de vida.',
    )
    ifdw_origin_lead_id = fields.Many2one(
        'crm.lead',
        string='Oportunidad CRM de Origen',
        ondelete='set null',
        index=True,
        copy=False,
    )
    ifdw_transferred_project_ids = fields.Many2many(
        'project.project',
        'ifdw_dms_file_transferred_project_rel',
        'dms_file_id',
        'project_id',
        string='Proyectos a los que ya se traspasó',
        copy=False,
        help='Registra a qué proyectos ya ha sido enviado este archivo para evitar duplicidades en segundos proyectos si se elige la Opción B en CRM.',
    )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if (
            domain
            and self.env.context.get('ifdw_hierarchical_files')
            and not self.env.context.get('ifdw_disable_child_of_directory')
        ):
            new_domain = []
            for item in domain:
                if (
                    isinstance(item, (list, tuple))
                    and len(item) == 3
                    and item[0] == 'directory_id'
                    and item[1] == '='
                    and isinstance(item[2], int)
                ):
                    new_domain.append(('directory_id', 'child_of', item[2]))
                else:
                    new_domain.append(item)
            domain = new_domain
        return super()._search(domain, offset=offset, limit=limit, order=order)


class IfdwDmsCrmTransferLog(models.Model):
    _name = 'ifdw.dms.crm.transfer.log'
    _description = 'Historial de Traspaso de Archivos'
    _order = 'transfer_date desc, id desc'

    lead_id = fields.Many2one('crm.lead', string='Oportunidad CRM', required=True, ondelete='cascade')
    project_id = fields.Many2one('project.project', string='Proyecto Destino', ondelete='set null')
    sale_order_id = fields.Many2one('sale.order', string='Pedido de Venta', ondelete='set null')
    transfer_date = fields.Datetime(string='Fecha de Traspaso', default=fields.Datetime.now, readonly=True)
    files_count = fields.Integer(string='Archivos Traspasados', readonly=True)
    operation_mode = fields.Char(string='Acción Aplicada', readonly=True)
    crm_policy_used = fields.Char(string='Filtro de Oportunidad', readonly=True)


class MailThreadDmsUniversal(models.AbstractModel):
    _inherit = 'mail.thread'

    dms_directory_id = fields.Many2one(
        'dms.directory',
        string='Carpeta DMS',
        compute='_compute_dms_automation_state',
    )
    dms_file_count = fields.Integer(
        string='Documentos',
        compute='_compute_dms_automation_state',
    )
    show_dms_smart_button = fields.Boolean(
        string='Mostrar Smart Button DMS',
        compute='_compute_dms_automation_state',
    )

    def _get_active_automation_rule(self):
        return self.env['ifdw.dms.automation'].sudo().search([
            ('active', '=', True),
            ('model_name', '=', self._name),
        ], order='sequence, id', limit=1)

    def _get_active_satellite_lines(self):
        return self.env['ifdw.dms.automation.satellite.line'].sudo().search([
            ('satellite_model_id.model', '=', self._name),
            ('automation_id.active', '=', True),
        ], order='sequence, id')

    def _find_dms_directory_for_rule(self, rule):
        self.ensure_one()
        Directory = self.env['dms.directory'].sudo()
        if not rule or not rule.storage_id or not self.id:
            return Directory

        storage_id = rule.storage_id.id
        molde_id = rule.template_root_dir_id.id if rule.template_root_dir_id else 0

        # Primero, búsqueda principal por vínculo técnico (res_model + res_id) en el almacenamiento de la regla
        if 'res_model' in Directory._fields and 'res_id' in Directory._fields:
            found = Directory.search([
                ('storage_id', '=', storage_id),
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('id', '!=', molde_id),
            ], limit=1)
            if found:
                return found

        # Segundo, fallback por ubicación y nombre (para carpetas creadas antes)
        target_name = rule._format_cloned_root_name(self)
        parent_dir = rule.parent_directory_id or rule.template_id.parent_directory_id
        dom = [
            ('storage_id', '=', storage_id),
            ('name', '=', target_name),
            ('id', '!=', molde_id),
        ]
        if parent_dir:
            dom.append(('parent_id', '=', parent_dir.id))
        else:
            dom.append(('is_root_directory', '=', True))

        found = Directory.search(dom, limit=1)
        if found and 'res_model' in Directory._fields and not found.res_id:
            found.write({'res_model': self._name, 'res_id': self.id})
        return found

    def _get_effective_dms_directory(self, rule=None):
        self.ensure_one()
        Directory = self.env['dms.directory'].sudo()
        if not self.id:
            return Directory

        own_rule = rule or self._get_active_automation_rule()
        if own_rule:
            found = self._find_dms_directory_for_rule(own_rule)
            if found:
                return found

        # Si el modelo actúa como Modelo Satélite (ej. Tarea -> Proyecto, Contrato -> Empleado, Pedido -> CRM)
        for sat in self._get_active_satellite_lines():
            field_name = sat.link_field_id.name
            if field_name and hasattr(self, field_name):
                parent_rec = getattr(self, field_name)
                if parent_rec and hasattr(parent_rec, '_get_effective_dms_directory'):
                    parent_dir = parent_rec._get_effective_dms_directory(rule=sat.automation_id)
                    if parent_dir:
                        return parent_dir
        return Directory

    def _compute_dms_automation_state(self):
        own_rule = self._get_active_automation_rule()
        sat_lines = self._get_active_satellite_lines()
        sat_show = any(sat.automation_id.show_smart_button for sat in sat_lines)
        for rec in self:
            directory = rec._get_effective_dms_directory(rule=own_rule)
            rec.dms_directory_id = directory.id if directory else False
            rec.dms_file_count = directory.count_total_files if directory else 0
            rec.show_dms_smart_button = (
                bool(own_rule and own_rule.show_smart_button)
                or sat_show
                or bool(directory)
            )

    def _ensure_dms_directory_by_rule(self, rule=None):
        self.ensure_one()
        rule = rule or self._get_active_automation_rule()
        if not rule:
            return self.env['dms.directory']
        effective = self._find_dms_directory_for_rule(rule)
        if effective:
            return effective

        new_dir = rule._clone_template_for_record(self)
        if new_dir:
            if (
                'dms_directory_id' in self._fields
                and not self._fields['dms_directory_id'].compute
                and not self._fields['dms_directory_id'].related
            ):
                self.sudo().with_context(ifdw_skip_dms_clone=True).write({'dms_directory_id': new_dir.id})
            src_rule, dst_rule = rule._get_effective_dest_rule_and_source_rule()
            if dst_rule and dst_rule == rule:
                rule._execute_file_movement_from_origin(self, new_dir)
        return new_dir

    def action_open_dms_directory(self):
        self.ensure_one()
        directory = self._get_effective_dms_directory()
        if not directory:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin documentos en este almacenamiento'),
                    'message': _('No hay carpeta activa en este flujo (los archivos aún no se han generado o fueron movidos y borrados del origen).'),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documentos: %s') % self.display_name,
            'res_model': 'dms.file',
            'view_mode': 'kanban,list,form',
            'domain': [('directory_id', 'child_of', directory.id)],
            'context': {
                'default_directory_id': directory.id,
                'searchpanel_default_directory_id': directory.id,
                'ifdw_hierarchical_files': True,
            },
        }

    @api.model
    def _hide_redundant_attachment_buttons_in_arch(self, btn_box):
        """Oculta botones nativos o de OCA que abren ir.attachment cuando el modelo usa DMS."""
        att_method_names = {
            'attachment_tree_view',
            'action_get_attachment_tree_view',
            'action_get_attachment_view',
            'action_open_attachments',
        }
        att_field_names = {'doc_count', 'attachment_number', 'attachment_count'}
        ActWindow = self.env['ir.actions.act_window'].sudo()

        for btn in btn_box.xpath(".//button"):
            btn_name = (btn.get('name') or '').strip()
            if not btn_name or btn_name == 'action_open_dms_directory':
                continue
            hide_btn = False
            if btn_name in att_method_names:
                hide_btn = True
            elif any(f.get('name') in att_field_names for f in btn.xpath(".//field")):
                hide_btn = True
            elif btn.get('type') == 'action' and btn_name.isdigit():
                act = ActWindow.browse(int(btn_name)).exists()
                if act and act.res_model == 'ir.attachment':
                    hide_btn = True
            if hide_btn:
                btn.set('invisible', 'True')

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form' and arch is not None:
            try:
                own_rule = self._get_active_automation_rule()
                sat_lines = self._get_active_satellite_lines()
                if own_rule or sat_lines:
                    button_boxes = arch.xpath("//div[@name='button_box']")
                    if button_boxes:
                        from lxml import etree
                        btn_box = button_boxes[0]
                        self._hide_redundant_attachment_buttons_in_arch(btn_box)
                        if not btn_box.xpath(".//button[@name='action_open_dms_directory']"):
                            inv_field = etree.Element('field', {
                                'name': 'show_dms_smart_button',
                                'invisible': '1',
                            })
                            btn = etree.Element('button', {
                                'name': 'action_open_dms_directory',
                                'type': 'object',
                                'class': 'oe_stat_button',
                                'icon': 'fa-folder-open',
                                'invisible': 'not show_dms_smart_button',
                            })
                            etree.SubElement(btn, 'field', {
                                'name': 'dms_file_count',
                                'widget': 'statinfo',
                                'string': _('Doc. DMS'),
                            })
                            btn_box.insert(0, btn)
                            btn_box.insert(0, inv_field)
            except Exception as e:
                _logger.warning("Aviso en _get_view DMS para %s: %s", self._name, e)
        return arch, view

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if (
            self.env.context.get('ifdw_skip_dms_clone')
            or self.env.context.get('install_mode')
            or self._name in ('dms.directory', 'dms.file', 'ifdw.dms.automation', 'mail.message')
        ):
            return records

        rule = self._get_active_automation_rule()
        if rule and rule.auto_clone_on_create:
            for rec in records:
                try:
                    if rule._record_matches_domain(rec):
                        rec._ensure_dms_directory_by_rule(rule)
                except Exception as e:
                    _logger.warning("Aviso al clonar plantilla DMS en %s(%s): %s", self._name, rec.id, e)
        return records

    def write(self, vals):
        res = super().write(vals)
        if (
            self.env.context.get('ifdw_skip_dms_clone')
            or self.env.context.get('install_mode')
            or self._name in ('dms.directory', 'dms.file', 'ifdw.dms.automation', 'mail.message')
        ):
            return res

        rule = self._get_active_automation_rule()
        if not rule:
            return res

        src_rule, dst_rule = rule._get_effective_dest_rule_and_source_rule()
        link_field = (dst_rule.origin_link_field_id or src_rule.out_origin_link_field_id) if (src_rule and dst_rule) else False
        trigger_fields = {'sale_order_id', 'sale_line_id'}
        if link_field and link_field.name:
            trigger_fields.add(link_field.name)

        for rec in self:
            try:
                if (trigger_fields & set(vals.keys())) and rule._record_matches_domain(rec):
                    rec_dir = rec._ensure_dms_directory_by_rule(rule)
                    if rec_dir and dst_rule and dst_rule == rule:
                        rule._execute_file_movement_from_origin(rec, rec_dir)

                if 'name' in vals:
                    directory = rec._find_dms_directory_for_rule(rule)
                    if directory:
                        directory.sudo().write({'name': rule._format_cloned_root_name(rec)})
            except Exception as e:
                _logger.warning("Aviso actualizando DMS en %s(%s): %s", self._name, rec.id, e)
        return res


class DmsAutomationRecordMixin(models.AbstractModel):
    _name = 'ifdw.dms.record.mixin'
    _description = 'Mixin de Conexión con Reglas de Automatización DMS'


class CrmLeadDms(models.Model):
    _name = 'crm.lead'
    _inherit = ['crm.lead', 'ifdw.dms.record.mixin']

    ifdw_project_transfer_policy = fields.Selection(
        selection=[
            ('global_rule', 'Opción A: Según regla global (Traspasar todos los archivos al crear Proyecto)'),
            ('only_new', 'Opción B: Traspasar solo archivos nuevos (No enviados ya a un Proyecto anterior)'),
            ('no_transfer', 'Opción C: No traspasar archivos automáticamente al próximo Proyecto (Crear carpeta limpia)'),
        ],
        string='Qué hacer con los archivos al crear Proyecto(s)',
        default='global_rule',
        required=True,
        help='Permite decidir granularmente en esta Oportunidad qué ocurrirá con sus archivos cuando se confirme un Presupuesto y se cree el Proyecto:\n'
             '- Opción A: Aplica el traspaso completo según la regla global de Automatización DMS.\n'
             '- Opción B: Envía al nuevo Proyecto únicamente los archivos nuevos subidos a esta oportunidad que todavía NO hayan sido enviados a un proyecto anterior.\n'
             '- Opción C: No envía ningún archivo de esta oportunidad al próximo proyecto que se genere.',
    )
    ifdw_transfer_log_ids = fields.One2many(
        'ifdw.dms.crm.transfer.log',
        'lead_id',
        string='Historial de Traspasos Documentales a Proyectos',
        readonly=True,
        help='Muestra el registro histórico de todos los traspasos de archivos realizados desde esta Oportunidad hacia Proyectos.',
    )


class SaleOrderDms(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'ifdw.dms.record.mixin']


class ProjectProjectDms(models.Model):
    _name = 'project.project'
    _inherit = ['project.project', 'ifdw.dms.record.mixin']


class ProjectTaskDms(models.Model):
    _inherit = 'project.task'



class IrActionsReportDmsSkip(models.Model):
    _inherit = 'ir.actions.report'

    def _postprocess_pdf_report(self, record, buffer):
        return super(
            IrActionsReportDmsSkip,
            self.with_context(skip_ifdw_attachment_hook=True)
        )._postprocess_pdf_report(record, buffer)


class IrAttachmentDmsRouter(models.Model):
    _inherit = 'ir.attachment'

    x_ifdw_dms_synced = fields.Boolean(string='Clasificado por Automatización DMS', default=False, copy=False)

    def _process_dms_automation_routing(self):
        if self.env.context.get('skip_ifdw_attachment_hook'):
            return
        Automation = self.env['ifdw.dms.automation'].sudo()
        Satellite = self.env['ifdw.dms.automation.satellite.line'].sudo()

        grouped_upload_logs = defaultdict(list)

        for att in self:
            if not att.res_model or not att.res_id or not att.datas or att.x_ifdw_dms_synced or att.res_field:
                continue
            if att.res_model in ('dms.file', 'dms.directory', 'mail.compose.message'):
                continue

            record = self.env[att.res_model].sudo().browse(att.res_id).exists()
            if not record:
                continue

            direct_rule = Automation.search([
                ('active', '=', True),
                ('model_name', '=', att.res_model),
            ], order='sequence, id', limit=1)

            if direct_rule and direct_rule._record_matches_domain(record):
                origin_label = getattr(record, 'name', False) or record.display_name
                info = direct_rule._classify_attachment_into_record_folder(
                    att, main_record=record, origin_label=origin_label, tag_name=False
                )
                if isinstance(info, dict):
                    grouped_upload_logs[(att.res_model, att.res_id)].append(info)
                continue

            sat_lines = Satellite.search([
                ('satellite_model_id.model', '=', att.res_model),
                ('automation_id.active', '=', True),
            ], order='sequence, id')

            matched_satellite = False
            for sat in sat_lines:
                field_name = sat.link_field_id.name
                if not field_name or not hasattr(record, field_name):
                    continue
                parent_record = getattr(record, field_name)
                if not parent_record:
                    continue
                rule = sat.automation_id
                if not rule._record_matches_domain(parent_record):
                    continue

                origin_label = getattr(record, 'name', False) or record.display_name
                tag_val = origin_label if sat.auto_tag_record_name else False
                info = rule._classify_attachment_into_record_folder(
                    att,
                    main_record=parent_record,
                    origin_label=origin_label,
                    tag_name=tag_val,
                    forced_template_subdir=sat.force_subdir_id,
                )
                if isinstance(info, dict):
                    grouped_upload_logs[(att.res_model, att.res_id)].append(info)
                matched_satellite = True
                break

            if not matched_satellite:
                # Red de seguridad Global (Ajustes > Documentos): si está activa, clasifica en las 10 carpetas por extensión
                global_info = self.env['ifdw.dms.general.folder.line'].sudo()._classify_attachment_global(att, record)
                if isinstance(global_info, dict):
                    grouped_upload_logs[(att.res_model, att.res_id)].append(global_info)

        for (res_model, res_id), info_list in grouped_upload_logs.items():
            self._post_chatter_upload_log(res_model, res_id, info_list)

    def _post_chatter_upload_log(self, res_model, res_id, info_list):
        if not info_list:
            return
        try:
            record = self.env[res_model].sudo().browse(res_id).exists()
            if not record or not hasattr(record, 'message_post'):
                return

            user_name = info_list[0].get('user_name') or self.env.user.name
            items_html = Markup("").join(
                Markup("<li><code>%s</code> ➔ <b><code>%s</code></b> <i>(📂 %s)</i></li>") % (
                    escape(item['original_name']),
                    escape(item['dms_name']),
                    escape(item['dest_folder_name']),
                )
                for item in info_list
            )
            body_html = Markup(
                "<div class='o_mail_notification'>"
                "📎 <b>Archivo(s) clasificado(s) en DMS</b> <i>(por %s)</i>:"
                "<ul class='mb-0'>%s</ul>"
                "</div>"
            ) % (escape(user_name), items_html)

            record.with_context(
                mail_create_nosubscribe=True,
                mail_notify_force_send=False,
                skip_ifdw_attachment_hook=True,
            ).message_post(
                body=body_html,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        except Exception as e:
            _logger.warning("No se pudo publicar nota de subida DMS en %s(%s): %s", res_model, res_id, e)

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        if not self.env.context.get('skip_ifdw_attachment_hook'):
            try:
                attachments._process_dms_automation_routing()
            except Exception as e:
                _logger.warning("Aviso en clasificador Chatter DMS (create): %s", e)
        return attachments

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_ifdw_attachment_hook') and ('res_model' in vals or 'res_id' in vals or 'datas' in vals):
            try:
                self._process_dms_automation_routing()
            except Exception as e:
                _logger.warning("Aviso en clasificador Chatter DMS (write): %s", e)
        return res

    def unlink(self):
        if not self.env.context.get('skip_ifdw_dms_unlink_sync'):
            try:
                Automation = self.env['ifdw.dms.automation'].sudo()
                Satellite = self.env['ifdw.dms.automation.satellite.line'].sudo()
                DmsFile = self.env['dms.file'].sudo()
                dms_files_to_unlink = DmsFile.browse()

                for att in self:
                    if not att.res_model:
                        continue
                    direct_rules = Automation.search([
                        ('active', '=', True),
                        ('sync_unlink_chatter', '=', True),
                        ('model_name', '=', att.res_model),
                    ])
                    sat_rules = Satellite.search([
                        ('automation_id.active', '=', True),
                        ('automation_id.sync_unlink_chatter', '=', True),
                        ('satellite_model_id.model', '=', att.res_model),
                    ]).mapped('automation_id')

                    active_rules = direct_rules | sat_rules
                    allowed_storage_ids = active_rules.mapped('storage_id').ids
                    ICP = self.env['ir.config_parameter'].sudo()
                    if ICP.get_param('ifdw_dms.enable_global_chatter_routing') == 'True':
                        gen_st_id = int(ICP.get_param('ifdw_dms.general_storage_id') or 0)
                        if gen_st_id:
                            allowed_storage_ids.append(gen_st_id)
                    if not allowed_storage_ids:
                        continue

                    linked_dms = DmsFile.with_context(ifdw_disable_child_of_directory=True).search([
                        ('ifdw_source_attachment_id', '=', att.id),
                        ('storage_id', 'in', allowed_storage_ids),
                    ])
                    unlocked_dms = linked_dms.filtered(
                        lambda f: not getattr(f, 'is_locked', False) and not getattr(f, 'locked_by', False)
                    )
                    dms_files_to_unlink |= unlocked_dms

                if dms_files_to_unlink:
                    dms_files_to_unlink.unlink()
            except Exception as e:
                _logger.warning("Aviso sincronizando papelera Chatter -> DMS: %s", e)
        return super().unlink()
