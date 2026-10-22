# -*- coding: utf-8 -*-
# Copyright 2026 Infinity Draw (https://infinitydraw.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from . import models
from odoo import _
from odoo.exceptions import UserError


def pre_init_check_oca_dms(env):
    missing = []
    for mod_name in ('dms', 'dms_field'):
        mod = env['ir.module.module'].sudo().search([
            ('name', '=', mod_name),
            ('state', '=', 'installed'),
        ], limit=1)
        if not mod:
            missing.append(mod_name)
    if missing:
        raise UserError(_(
            "Requisito previo no encontrado: Para instalar 'ifdw_dms_automation_workflow' "
            "debes instalar primero los módulos oficiales de la OCA: %s."
        ) % ', '.join(missing))
