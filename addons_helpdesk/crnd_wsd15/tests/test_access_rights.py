from odoo.addons.generic_request15.tests.common import AccessRightsCase
from odoo import exceptions
from odoo.tools.misc import mute_logger


class TestWSDRequestAccessRights(AccessRightsCase):
    """Test request access rules
    """

    @classmethod
    def setUpClass(cls):
        super(TestWSDRequestAccessRights, cls).setUpClass()

        # Users
        cls.demo_test_user_1 = cls.env['res.users'].create({
            'name': 'Test user',
            'login': 'demo_test_user_1',
            'password': 'demo',
        })

        # Envs
        cls.ut_env = cls.env(user=cls.demo_test_user_1)

        # Request Type
        cls.ut_simple_type = cls.ut_env.ref(
            'generic_request15.request_type_simple')

        # Request category
        cls.ut_category_demo_general = cls.ut_env.ref(
            'generic_request15.request_category_demo_general')

    def test_category_acces_rights_0010(self):

        with mute_logger('odoo.models'):
            with self.assertRaises(exceptions.AccessError):
                # pylint: disable=pointless-statement
                self.ut_category_demo_general.with_user(
                    self.demo_test_user_1).read(['name'])

        simple_group = self.env['res.groups'].create({
            'name': 'Test simple group'
        })
        self.assertFalse(
            simple_group in
            self.ut_category_demo_general.sudo().access_group_ids)

        # Add to Request Category Access Group new simple_group
        self.ut_category_demo_general.sudo().write({
            'access_group_ids': [(4, simple_group.id)],
        })

        self.assertTrue(
            simple_group in
            self.ut_category_demo_general.sudo().access_group_ids)

        with mute_logger('odoo.models'):
            with self.assertRaises(exceptions.AccessError):
                # pylint: disable=pointless-statement
                self.ut_category_demo_general.with_user(
                    self.demo_test_user_1).read(['name'])

        website_user = self.env.ref(
            'crnd_wsd15.group_service_desk_website_user')

        self.assertTrue(self.demo_test_user_1 in website_user.users)

        # Add demo-user to 'simple_group'
        self.demo_test_user_1.groups_id |= simple_group

        # Ensure, after adding to group simple_group the
        # simple_category is readable
        self.assertTrue(
            self.ut_category_demo_general.with_user(
                self.demo_test_user_1).read(['name']))

    def test_type_access_rights_0010(self):
        with mute_logger('odoo.models'):
            with self.assertRaises(exceptions.AccessError):
                # pylint: disable=pointless-statement
                self.ut_simple_type.with_user(
                    self.demo_test_user_1).read(['name'])

        simple_group = self.env['res.groups'].create({
            'name': 'Test simple group'
        })
        self.assertFalse(
            simple_group in
            self.ut_simple_type.sudo().access_group_ids)

        # Add to Request Category Access Group new simple_group
        self.ut_simple_type.sudo().write({
            'access_group_ids': [(4, simple_group.id)],
        })

        self.assertTrue(
            simple_group in
            self.ut_simple_type.sudo().access_group_ids)

        with mute_logger('odoo.models'):
            with self.assertRaises(exceptions.AccessError):
                # pylint: disable=pointless-statement
                self.ut_simple_type.with_user(
                    self.demo_test_user_1).read(['name'])

        website_user = self.env.ref(
            'crnd_wsd15.group_service_desk_website_user')
        # self.assertFalse(self.demo_test_user_1 in website_user.users)

        # Add demo-user to 'website_user'
        # self.demo_test_user_1.groups_id |= website_user

        self.assertTrue(self.demo_test_user_1 in website_user.users)

        # Add demo-user to 'simple_group'
        self.demo_test_user_1.groups_id |= simple_group

        # Ensure, after adding to group simple_group the
        # simple_category is readable
        self.assertTrue(self.ut_simple_type.with_user(
            self.demo_test_user_1).read(['name']))
