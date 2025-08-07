{
    "name": "Multi-print",
    "summary": """
      Allow to print and zip multiple documents at once
    """,
    "description": """
      Allow to print and zip multiple documents at once
    """,
    "author": "Log'in Line",
    "website": "https://www.loginline.com",
    "category": "Technical",
    "version": "0.1",
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/menu.xml",
        "views/print_pdf_wizard.xml",
        "views/print_action.xml",
        "data/cron.xml",
    ],
    "qweb": [],
    "assets": {
        "web.assets_backend": [
            "multi_print/static/src/fields.scss",
        ],
    },
    "depends": ["web", "mail"],
    'images': ['static/description/banner.png'],
}
# -*- coding: utf-8 -*-
