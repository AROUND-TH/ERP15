# -*- coding: utf-8 -*-

{
    "name": "Excel Import/Export/Report MRP",
    "version": "14.0.1.0.0",
    "author": "Around Enterprise Consulting Co., Ltd.",
    "website": "https://www.around.co.th",
    "category": "Tools",
    "depends": ["excel_import_export", "mrp", "mrp_planning_engine","custom_success_message"],
    "data": [
        "import_export_mrp_demand/templates.xml",
        "import_export_mrp_demand/result_mrp_demand.xml",
        "import_export_mrp_demand/security/ir.model.access.csv",
        "import_export_mrp_parameter/actions.xml",
        "import_export_mrp_parameter/templates.xml",
        "import_export_mrp_production/security/ir.model.access.csv",
        "import_export_mrp_production/wizard_import_mrp_production_view.xml",
        "import_export_mrp_planned_order/security/ir.model.access.csv",
        "import_export_mrp_planned_order/wizard_import_mrp_planned_orders_view.xml",
        "import_export_mrp_bom/wizard_import_mrp_bom_view.xml",
        "import_export_mrp_bom/security/ir.model.access.csv",
        "views/mrp_bom.xml",
    ],
    "installable": True,
    "development_status": "Prod",
    "maintainers": ["Golf2SKY"],
}
