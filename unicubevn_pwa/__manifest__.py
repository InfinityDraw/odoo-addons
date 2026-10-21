{
    'name': "PWA y Notificaciones (via Firebase)",
    'summary': """PWA y Notificacions Push mediante Firebase por Infinity Draw""",

    'description': """
        Este módulo permite personalizar la configuración del Proresive Web APP (PWA) integrado de Odoo:
            - Cambiar el nombre del PWA
            - Cambiar el logo del PWA
            - Agregar ruta personalizada
            - Agregar notificación push mediante Firebase (FCM v1)
    """,

    'author': "Infinity Draw",
    'website': "https://infinitydraw.es",
    "license": "LGPL-3",
    'category': 'Infinity Draw/Utilities',
    "sequence": 200,
    'version': '17.0.0.1',
    'support': 'ayuda-mantenimiento@infinitydraw.es',
    "application": True,
    "installable": True,

    # módulos necesarios para el correcto funcionamiento de éste.
    'depends': ['base', 'web', 'website',],

    "images": ["static/description/image.jpg"],

    # Siempre carga
    'data': [
        'security/ir.model.access.csv',
        'views/push_notification.xml',
        'views/res_config.xml',
        'views/webclient_templates.xml',


    ],
    'assets': {
        'web.assets_backend': [
            "unicubevn_pwa/static/src/js/firebase-app.js",
            "unicubevn_pwa/static/src/js/firebase-messaging.js",
            "unicubevn_pwa/static/src/js/firebase.js"
        ],
    },
    "external_dependencies": {"python": ["firebase-admin"]},
}
