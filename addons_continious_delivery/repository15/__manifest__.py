{
    "name": "Repository",
    "version": "1.0",
    "author": "Sandas",
    "website": "www.sandas.lt",
    "category": "Base",
    "depends": ["base", "application_server15"],
    "data": [
        "views/repository_view.xml",
        "views/branch_view.xml",
        "views/res_users_view.xml",
        "security/ir.model.access.csv"
    ],
    "description": """ Abstract repository functionality integrate different versioning systems 
        (for example subversion, bazaar, etc) to Open ERP.
    """,
    "license": "Other proprietary",
    "installable": True,
    "active": False,
}
