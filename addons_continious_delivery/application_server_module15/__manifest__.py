{
    "name": "Application Server Module",
    "version": "1.0",
    "author": "Sandas",
    "website": "www.sandas.eu",
    "category": "Base",
    "depends": ["application_server15", "repository15"],
    "init_xml": [],
    "demo_xml": [],
    "data": [
        "views/module_view.xml",
        "views/module_version.xml",
        "views/repository_view.xml",
        "security/ir.model.access.csv",
    ],
    "description":
        """
        Create and administer application modules.
        """,
    "license": "Other proprietary",
    "installable": True,
    "active": False,
}
