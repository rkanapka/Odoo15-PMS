{
    "name": "Application Server",
    "version": "1.0",
    "author": "Sandas",
    "website": "www.sandas.lt",
    "category": "Sandas",
    "depends": ["base", "mail"],
    "data": [
        "views/application_view.xml",
        "views/server_view.xml",
        "security/ir.model.access.csv",
    ],
    "description":
        """
        Create versioned server applications, for example Odoo.
        Register servers you are administrating and which applications is installed in those servers.
        Installations is registered in special installation form.
        """,
    "license": "Other proprietary",
    "installable": True,
    "active": False,
}
