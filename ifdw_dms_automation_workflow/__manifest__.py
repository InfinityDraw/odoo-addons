# -*- coding: utf-8 -*-
# Copyright 2026 Infinity Draw (https://infinitydraw.es)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    'name': 'Automatización flujos y archivos del DMS',
    'version': '18.0.7.0.0',
    'category': 'Document Management',
    'summary': 'Automatización DMS configurable con soporte A->B->C, borrado estanco, candado DMS y trazabilidad en Chatter',
    'description': """
Automatización flujos y archivos del DMS
======================================================
Módulo desarrollado por Infinity Draw para gobernar desde interfaz gráfica toda la automatización documental sobre OCA DMS:

* Nuevo submenú en Documentos > Configuración > Organizar > Automatización DMS.
* Conexión directa con 'Plantillas DMS embebidas' (dms.field.template) respetando los almacenamientos, modelos, grupos y estructuras de carpetas ya creadas por el administrador.
* Cabecera configurable con clonado automático por filtro de dominio, vista previa de Smart Button, selector de formatos de auto-renombrado y filtro regulable (1 KB a 100 KB, por defecto 30 KB) contra imágenes basura de firmas de correo.
* Pestaña 1 (Reg. Chatter Auto-clasific.): Mapeo visual entre las subcarpetas de la plantilla, tipos de archivo (Fotos, Vídeos, Audios, Planos CAD/BC3, Ofimática/PDF, Otros) y Categorías DMS.
* Pestaña 2 (Reg. Mod. Auto-clasific.): Vinculación de modelos satélite (ej. Tareas -> Proyecto, Pedidos -> Oportunidad, Facturas -> Proyecto) con autodetección del campo relacional.
* Pestaña 3 (Reg. Mov. Archiv.): Reglas de traslado o copia de archivos entre flujos (ej. de Ventas a Proyectos al aprobarse el presupuesto con servicio de proyecto), con opción por defecto de copiar manteniendo originales por seguridad.
* Pestaña 'Ops. Documentos' en CRM (crm.lead) para control granular de traspaso en segundos proyectos o ampliaciones.
* Filtro 'child_of' aplicado exclusivamente en 'Documentos > Archivos' y Smart Buttons (evitando duplicados visuales en 'Documentos > Documentos').
* Soporte completo para cadenas 'A -> B -> C' en Pestaña 3 separando canales de Entrada y Salida en espejo.
* Sincronización de borrado desde el chatter haciendo que sea estanca por almacenamiento y respeto absoluto al bloqueo nativo ('Bloquear') del DMS.
* Nota agrupada en el Chatter al clasificar archivos subidos manualmente (ignorando PDFs autogenerados de informes).
    """,
    'author': 'Infinity Draw',
    'maintainer': 'Infinity Draw',
    'website': 'https://infinitydraw.es',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'crm',
        'sale_management',
        'project',
        'sale_project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dms_automation_views.xml',
        'views/dms_business_views.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'pre_init_hook': 'pre_init_check_oca_dms',
    'installable': True,
    'application': False,
    'auto_install': False,
}
