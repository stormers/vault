# -*- coding:utf-8 -*-

from uuid import uuid4
from unittest import TestCase
from mock import patch
from keystoneclient.v2_0.tenants import Tenant
from keystoneclient.openstack.common.apiclient import exceptions

from django.conf import settings
from django.contrib.auth.models import User, Group

from identity.keystone import Keystone
from identity.tests.fakes import UserFactory, GroupFactory, FakeResource

from vault.tests.fakes import fake_request
from vault.models import GroupProjects


class TestKeystoneV2(TestCase):
    """ Test keystone version 2 """

    @classmethod
    def tearDownClass(cls):
        for item in [User, Group, GroupProjects]:
            item.objects.all().delete()

    def setUp(self):
        self.request = fake_request()

        self.project = Tenant('123', {
            u'id': str(uuid4()),
            u'name': 'project_test',
            u'description': 'project description',
            u'enabled': True
        })

        self.mock_project_create = patch(
            'identity.keystone.Keystone.project_create').start()
        self.mock_project_create.return_value = self.project

        self.mock_project_update = patch(
            'identity.keystone.Keystone.project_update').start()
        self.mock_project_update.return_value = self.project

        fake_project = FakeResource(n='abcdefg', name='fake_project')
        fake_project.description = 'desc do fake'

        self.mock_project_get = patch(
            'identity.keystone.Keystone.project_get').start()
        self.mock_project_get.return_value = fake_project

        self.mock_bs_project = patch(
            'storm_keystone.keystone.Keystone.vault_business_service_project_create').start()

        self.mock_keystone_conn = patch(
            'storm_keystone.keystone.Keystone._create_keystone_connection').start()

        self.group = GroupFactory(id=1)

    def tearDown(self):
        self.group.delete()
        patch.stopall()

    def test_user_list_valid_project_id(self):
        """
        Testa metodo de listagem de usuario para o caso de um project_id valido
        que possui usuarios
        """
        expected = ['uma', 'lista', 'qualquer']

        self.mock_keystone_conn.return_value.users.list.return_value = expected
        keystone = Keystone(self.request)

        computed = keystone.user_list(project_id='123454321')

        self.assertEqual(computed, expected)

    def test_user_list_valid_project_id_with_no_user(self):
        """
        Testa metodo de listagem de usuario para o caso de um project_id valido
        que NAO possui usuarios
        """
        expected = []

        self.mock_keystone_conn.return_value.users.list.return_value = expected
        keystone = Keystone(self.request)

        computed = keystone.user_list(project_id='123454321')

        self.assertEqual(computed, expected)

    def test_user_list_invalid_project(self):
        """
        Testa metodo de listagem de usuario para o caso de um project_id
        invalido
        """
        self.mock_keystone_conn.return_value.users.list.side_effect = exceptions.NotFound
        keystone = Keystone(self.request)

        self.assertRaises(exceptions.NotFound, keystone.user_list)

    @patch('identity.keystone.Keystone.add_user_role')
    def test_keystone_create_user_with_no_role(self, mock_add_user_role):
        """ Cadastra usuario sem setar role para nenhum project """

        keystone = Keystone(self.request)
        keystone.user_create('name', email='email@email.com',
                             password='password', project_id='project_id',
                             enabled=True)

        keystone.conn.users.create.assert_called_with('name', 'password', 'email@email.com', 'project_id', True)
        self.assertFalse(mock_add_user_role.called)

    @patch('identity.keystone.Keystone.add_user_role')
    @patch('identity.keystone.Keystone.project_get')
    @patch('identity.keystone.Keystone.role_get')
    def test_keystone_create_user_and_set_role(self, mock_role_get, mock_project_get, mock_add_user_role):
        """ Cadastra usuario e seta role para project """

        mock_user_create = self.mock_keystone_conn.return_value.users.create

        fake_user = FakeResource('user_id', name='user_name')
        fake_role = FakeResource('role_id', name='role_name')
        fake_project = FakeResource('project_id', name='project_name')

        mock_user_create.return_value = fake_user
        mock_role_get.return_value = fake_role
        mock_project_get.return_value = fake_project

        keystone = Keystone(self.request, 'tenant_name')
        keystone.user_create('name', email='email@email.com',
                             password='password', project_id='project_id',
                             enabled=True, role_id='role_id')

        keystone.conn.users.create.assert_called_with('name', 'password', 'email@email.com', 'project_id', True)
        mock_add_user_role.assert_called_with(fake_user, fake_project, fake_role)

    @patch('identity.keystone.Keystone.user_create')
    @patch('storm_keystone.keystone.Keystone.create_password')
    @patch('storm_keystone.keystone.Keystone.vault_group_project_create')
    def test_vault_create_project(self, mock_gp_create, mock_key_pass, mock_key_user):

        mock_key_user.return_value = FakeResource(n=self.project.id, name='u_{}'.format(self.project.name))
        mock_key_pass.return_value = 'password'

        keystone = Keystone(self.request, tenant_name='tenant_name')

        expected = {
            'status': True,
            'project': self.mock_project_create.return_value,
            'user': mock_key_user.return_value,
            'password': mock_key_pass.return_value,
        }

        computed = keystone.vault_project_create(self.project.name, self.group.id,
                                                 description=self.project.description)

        # Criacao do Project
        self.mock_project_create.assert_called_with(self.project.name,
                                                    description=self.project.description,
                                                    enabled=True)

        # Criacao do User
        mock_key_user.assert_called_with(name='u_{}'.format(self.project.name),
                                         password='password',
                                         project_id=self.project.id,
                                         role_id=settings.KEYSTONE_ROLE)

        mock_gp_create.assert_called_with(group_id=self.group.id,
                                          project_id=self.project.id,
                                          owner=1)

        self.assertEqual(computed, expected)

    @patch('identity.keystone.Keystone.user_create')
    def test_vault_create_project_forbidden_on_project_create(self, mock_key_user):

        self.mock_project_create.side_effect = exceptions.Forbidden
        mock_key_user.return_value = FakeResource(n=self.project.id, name='u_{}'.format(self.project.name))

        keystone = Keystone(self.request, tenant_name='tenant_name')

        expected = {'status': False, 'reason': 'Superuser required.'}
        computed = keystone.vault_project_create(self.project.name, 1, description=self.project.description)

        self.assertEqual(computed, expected)

        # Criacao de user nao pode ocorrer quando hover falha na criacao do project
        self.assertFalse(mock_key_user.called)

    @patch('identity.keystone.Keystone.project_create')
    @patch('identity.keystone.Keystone.project_delete')
    @patch('identity.keystone.Keystone.user_create')
    def test_vault_create_project_forbidden_on_user_create(self, mock_key_user,
                                                                 mock_project_delete,
                                                                 mock_project_create):

        mock_project_create.return_value = Tenant('123',
            {u'id': self.project.id, u'name': self.project.name})
        mock_key_user.side_effect = exceptions.Forbidden

        keystone = Keystone(self.request, tenant_name='tenant_name')

        expected = {'status': False, 'reason': 'Admin required'}
        computed = keystone.vault_project_create(self.project.name, 1, description=self.project.description)

        self.assertEqual(computed, expected)

        # Se falhou o cadastro de usuario, o project devera ser deletado
        mock_project_delete.assert_called_with(self.project.id)

    @patch('identity.keystone.Keystone.project_delete')
    @patch('identity.keystone.Keystone.user_create')
    @patch('identity.keystone.Keystone.user_delete')
    @patch('identity.keystone.GroupProjects.save')
    def test_vault_create_project_fail_to_save_group_project_on_db(self, mock_gp_save,
                                                                         mock_user_delete,
                                                                         mock_user_create,
                                                                         mock_project_delete):

        fake_user = FakeResource(n=self.project.id, name='u_{}'.format(self.project.name))
        mock_user_create.return_value = fake_user

        # Excecao ao salvar no db
        mock_gp_save.side_effect = Exception

        keystone = Keystone(self.request, tenant_name='tenant_name')

        expected = {'status': False, 'reason': 'Unable to assign project to group'}
        computed = keystone.vault_project_create(self.project.name, 2, description=self.project.description)

        self.assertEqual(computed, expected)

        mock_project_delete.assert_called_with(self.project.id)

        mock_user_delete.assert_called_with(fake_user.id)

    @patch('identity.keystone.Keystone.user_list')
    @patch('identity.keystone.Keystone.project_get')
    def test_find_user_with_u_prefix(self, mock_project_get, mock_user_list):
        mock_project_get.return_value = Tenant('123',
            {u'id': 'abcde', u'name': 'infra'})
        mock_user_list.return_value = UserFactory(id='abcde', username='u_project_test')

        keystone = Keystone(self.request, tenant_name='tenant_name')

        fake_user = 'u_{}'.format(self.project.name)
        self.assertEqual(fake_user, mock_user_list.return_value.username)

    def test_vault_update_project_keystone(self):
        group_id = self.group.id
        keystone = Keystone(self.request, tenant_name='tenant_name')
        fake_project = self.mock_project_get.return_value

        expected = {'status': True,
                    'project': self.mock_project_update.return_value}

        computed = keystone.vault_project_update(self.project.id,
                                                 self.project.name,
                                                 group_id,
                                                 description=self.project.description)
        self.assertEqual(computed, expected)


class TestKeystoneDeleteProject(TestCase):

    def setUp(self):
        self.request = fake_request()

        self.user_id = 'abcdefghiklmnopq'
        self.user_name = 'user_name'

        self.project = Tenant('321', {
            u'id': str(uuid4()),
            u'name': 'project_test_delete',
            u'description': 'project test delete description',
            u'enabled': True
        })

        self.mock_keystone_conn = patch('storm_keystone.keystone.Keystone._create_keystone_connection').start()

        self.mock_project_get_by_name = patch('storm_keystone.keystone.Keystone.project_get_by_name').start()
        self.mock_project_get_by_name.return_value = self.project

        self.mock_find_user_with_u_prefix = patch('storm_keystone.keystone.Keystone.find_user_with_u_prefix').start()
        self.mock_find_user_with_u_prefix.return_value = FakeResource(self.user_id, name=self.user_name)

    def tearDown(self):
        patch.stopall()

    @patch('storm_keystone.keystone.Keystone.project_delete')
    @patch('storm_keystone.keystone.Keystone._project_delete_swift')
    @patch('storm_keystone.keystone.Keystone.get_object_store_endpoints')
    def test_vault_delete_project(self, mock_endpoints,
                                        mock_swift_delete,
                                        mock_keystone_delete):
        mock_endpoints.return_value = {'adminURL': 'https://fake.api.globoi.com/v1/AUTH_XPTO'}

        class FakeResponse(object):
            status_code = 204
        mock_swift_delete.return_value = FakeResponse()

        keystone = Keystone(self.request)
        _ = keystone.vault_project_delete(self.project.name)

        # Swift project delete
        mock_swift_delete.assert_called_with(self.project.id)

        # Find project's user
        self.mock_find_user_with_u_prefix.assert_called_with(self.project.id)

        # Keystone project delete
        mock_keystone_delete.assert_called_with(self.project.id)


class TestKeystonePermissionToConnect(TestCase):
    """
    This tests are separated because it can't mock mock_keystone_is_allowed
    method
    """

    def setUp(self):
        self.request = fake_request()
        self.mock_filter = patch('identity.keystone.GroupProjects.objects.filter').start()
        patch('storm_keystone.keystone.Keystone._create_keystone_connection').start()

    def tearDown(self):
        patch.stopall()

    def test_superuser_creates_keystone_conn(self):
        self.mock_filter.return_value = None
        self.conn = Keystone(self.request, tenant_name='tenant_name')
        self.assertTrue(isinstance(self.conn, Keystone))

    def test_regular_user_creates_keystone_conn_on_a_allowed_project(self):

        # Se este mock retorna uma lista nao vazia, significa que o time do
        # usuario possui permissao no project
        self.mock_filter.return_value = [1]

        self.request.user.is_superuser = False
        self.conn = Keystone(self.request, tenant_name='tenant_name')

        self.assertTrue(isinstance(self.conn, Keystone))

    def test_regular_user_creates_keystone_conn_on_a_NOT_allowed_project(self):

        # Se este mock retorna uma lista  vazia, significa que o time do
        # usuario NAO possui permissao no project
        self.mock_filter.return_value = []
        self.request.user.is_superuser = False

        keystone = Keystone(self.request, tenant_name='abcdefg')
        self.assertEqual(keystone.conn, None)
