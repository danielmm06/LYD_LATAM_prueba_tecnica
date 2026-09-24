{
    'name': "Sale Record Import & Dashboard",
    'summary': "Import sales from Excel, analyze them on a dashboard and follow new sales in real time.",
    'description': """
Sale Record Import & Dashboard
===============================
Import monthly sales from an Excel file, store them as sale records, analyze
them on a commercial dashboard (list, graph, pivot with KPI cards) and see
new sale records appear on the list in real time, without reloading the page.
""",
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'license': 'LGPL-3',
    'author': "LYD LATAM",
    'depends': ['base', 'web', 'bus', 'product'],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'data': [
        'security/lyd_sale_record_groups.xml',
        'security/ir.model.access.csv',
        'security/lyd_sale_record_security.xml',
        'views/lyd_sale_record_views.xml',
        'report/lyd_sale_record_report_views.xml',
        'wizard/lyd_sale_record_import_views.xml',
        'views/lyd_sale_record_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'lyd_sale_record/static/src/views/**/*',
        ],
        'web.assets_unit_tests': [
            'lyd_sale_record/static/tests/**/*',
        ],
    },
    'application': True,
    'installable': True,
}
