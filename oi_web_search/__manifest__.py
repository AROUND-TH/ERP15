{
    "name": "Advance Search",
    "summary": "Advanced Search, List View Search, List View Manager, Global Search, Quick Search, Listview Search, Search Engine, Advance Search, Advance Filter, Field Search, Advance Search Tree",
    "version": "15.0.1.1.7",
    "category": "Extra Tools",
    "website": "https://www.open-inside.com",
    "description": """
        
    """,
    "website": "https://www.open-inside.com",
    "author": "Openinside",
    "license": "OPL-1",
    "price" : 85,
    "currency": 'USD',    
   
    "installable": True,
    # any module necessary for this one to work correctly
    "depends": [
       'web'
    ],

    # always loaded
    'data': [
       
    ],
    'qweb' : [
        
        ],    
    'assets': {
        'web.assets_backend': [
            'oi_web_search/static/src/js/search_menu.js',
            'oi_web_search/static/src/js/abstract_action.js',
            'oi_web_search/static/src/js/control_panel.js',
            'oi_web_search/static/src/css/custom.css',
            ],
        'web.assets_qweb': [
            'oi_web_search/static/src/xml/templates.xml'
            ]
        },        
    'images' : [
        'static/description/cover.png'
        ],      
    'odoo-apps' : True 
}