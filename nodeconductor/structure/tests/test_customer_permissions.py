from __future__ import unicode_literals

import collections

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework import test
from rest_framework.reverse import reverse

from nodeconductor.structure.models import CustomerRole, ProjectRole
from nodeconductor.structure.tests import factories

User = get_user_model()

TestRole = collections.namedtuple('TestRole', ['user', 'customer', 'role'])


class CustomerPermissionApiPermissionTest(test.APITransactionTestCase):
    all_roles = (
        # user customer role
        TestRole('first', 'first', 'owner'),

        TestRole('both', 'first', 'owner'),
        TestRole('both', 'second', 'owner'),
    )

    role_map = {
        'owner': CustomerRole.OWNER,
    }

    def setUp(self):
        self.users = {
            # 'staff': factories.UserFactory(is_staff=True),
            'first': factories.UserFactory(),
            'both': factories.UserFactory(),
            'no_role': factories.UserFactory(),
        }

        self.customers = {
            'first': factories.CustomerFactory(),
            'second': factories.CustomerFactory(),
        }

        for user, customer, role in self.all_roles:
            self.customers[customer].add_user(self.users[user], self.role_map[role])

    # No role tests
    def test_user_cannot_list_roles_within_customers_he_has_no_role_in(self):
        for login_user in self.users:
            self.client.force_authenticate(user=self.users[login_user])

            response = self.client.get(reverse('customer_permission-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            users_customers = set(r.customer for r in self.all_roles if r.user == login_user)
            unseen_roles = (r for r in self.all_roles if r.customer not in users_customers)

            for role in unseen_roles:
                role_url = self._get_permission_url(*role)

                urls = set([role['url'] for role in response.data])

                self.assertNotIn(
                    role_url, urls,
                    '{0} user sees privilege he is not supposed to see: {1}'.format(login_user, role),
                )

    # Customer owner tests
    def test_user_can_list_roles_within_customers_he_owns(self):
        for login_user in self.users:
            self.client.force_authenticate(user=self.users[login_user])

            response = self.client.get(reverse('customer_permission-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            users_customers = set(r.customer for r in self.all_roles if r.user == login_user)
            seen_roles = (r for r in self.all_roles if r.customer in users_customers)

            for role in seen_roles:
                role_url = self._get_permission_url(*role)

                urls = set([role['url'] for role in response.data])

                self.assertIn(
                    role_url, urls,
                    '{0} user does not see privilege he is supposed to see: {1}'.format(login_user, role),
                )

    def test_user_can_list_roles_within_customer_if_he_has_admin_role_in_a_project_owned_by_that_customer(self):
        admin_user = factories.UserFactory()
        project = factories.ProjectFactory(customer=self.customers['first'])
        project.add_user(admin_user, ProjectRole.ADMINISTRATOR)

        self.client.force_authenticate(user=admin_user)

        response = self.client.get(reverse('customer_permission-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        role_url = self._get_permission_url('first', 'first', 'owner')

        urls = set([role['url'] for role in response.data])

        self.assertIn(
            role_url, urls,
            '{0} user does not see privilege he is supposed to see: {1}'.format(admin_user, role_url),
        )

    # Helper methods
    def _get_permission_url(self, user, customer, role):
        permission = User.groups.through.objects.get(
            user=self.users[user],
            group__customerrole__role_type=self.role_map[role],
            group__customerrole__customer=self.customers[customer],
        )
        return 'http://testserver' + reverse('customer_permission-detail', kwargs={'pk': permission.pk})


class CustomerPermissionApiFiltrationTest(test.APISimpleTestCase):
    def setUp(self):
        staff_user = factories.UserFactory(is_staff=True)
        self.client.force_authenticate(user=staff_user)

        self.users = {
            'first': factories.UserFactory(),
            'second': factories.UserFactory(),
        }

        self.customers = {
            'first': factories.CustomerFactory(),
            'second': factories.CustomerFactory(),
        }

        for customer in self.customers:
            self.customers[customer].add_user(self.users['first'], CustomerRole.OWNER)
            self.customers[customer].add_user(self.users['second'], CustomerRole.OWNER)

    def test_staff_user_can_filter_roles_within_customer_by_customer_uuid(self):
        response = self.client.get(reverse('customer_permission-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for customer in self.customers:
            query = '?customer=%s' % self.customers[customer].uuid

            response = self.client.get(reverse('customer_permission-list') + query)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            customer_url = self._get_customer_url(self.customers[customer])

            for permission in response.data:
                self.assertEqual(customer_url, permission['customer'])

    def test_staff_user_can_filter_roles_within_customer_by_username(self):
        response = self.client.get(reverse('customer_permission-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for user in self.users:
            self._ensure_matching_entries_in('username', self.users[user].username)
            self._ensure_non_matching_entries_not_in('username', self.users[user].username)

    def test_staff_user_can_filter_roles_within_customer_by_native_name(self):
        response = self.client.get(reverse('customer_permission-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for user in self.users:
            self._ensure_matching_entries_in('native_name', self.users[user].native_name)
            self._ensure_non_matching_entries_not_in('native_name', self.users[user].native_name)

    def test_staff_user_can_filter_roles_within_customer_by_full_name(self):
        response = self.client.get(reverse('customer_permission-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for user in self.users:
            self._ensure_matching_entries_in('full_name', self.users[user].full_name)
            self._ensure_non_matching_entries_not_in('full_name', self.users[user].full_name)

    def test_staff_user_can_see_required_fields_in_filtration_response(self):
        response = self.client.get(reverse('customer_permission-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for customer in self.customers:
            query = '?customer=%s' % self.customers[customer].uuid

            response = self.client.get(reverse('customer_permission-list') + query)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            required_fields = ('url', 'user_native_name', 'user_full_name', 'user_username')

            for permission in response.data:
                for field in required_fields:
                    self.assertIn(field, permission)

    # Helper methods
    def _ensure_matching_entries_in(self, field, value):
        query = '?%s=%s' % (field, value)

        response = self.client.get(reverse('customer_permission-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('customer_permission-list') + query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for permission in response.data:
                self.assertEqual(value, permission['user_' + field])

    def _ensure_non_matching_entries_not_in(self, field, value):
        user = factories.UserFactory()

        customer = factories.CustomerFactory()
        customer.add_user(user, CustomerRole.OWNER)

        query = '?%s=%s' % (field, getattr(user, field))

        response = self.client.get(reverse('customer_permission-list') + query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for permission in response.data:
                self.assertNotEqual(value, permission['user_' + field])

    def _get_customer_url(self, customer):
        return 'http://testserver' + reverse('customer-detail', kwargs={'uuid': customer.uuid})
