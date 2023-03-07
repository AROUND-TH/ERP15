# -*- coding: utf-8 -*-

{
    'name': "Customize: Expenses",
    'summary': """
        Customize of Expenses Module 
    """,
    'description': """""",
    'author': "Around Enterprise Consulting Co., Ltd.",
    'website': "https://www.around.co.th",
    'category': 'Human Resources/Expenses',
    "version": "15",
    'depends': ['hr_expense'],
    'data': [
        'data/sequence.xml',
        'report/hr_expense_report.xml',
        'views/hr_expense_views.xml',
    ],
}
