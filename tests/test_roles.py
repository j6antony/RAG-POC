"""Role resolution and authentication client isolation regressions."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from fastapi import HTTPException
from pydantic import ValidationError
from test_knowledge import api, KnowledgeTests

spec = importlib.util.spec_from_file_location('roles_under_test', Path(__file__).resolve().parents[1] / 'src/authentification.py')
roles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roles)

class RoleTests(unittest.TestCase):
    def test_assigned_levels_and_multiple_roles(self):
        db = Mock()
        for assigned, expected in [(['user'], 1), (['manager'], 2), (['admin'], 3), (['user', 'manager'], 2)]:
            db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{'role': role} for role in assigned]
            self.assertEqual(roles.get_user_access(db, 'id'), expected)

    def test_missing_or_invalid_role_does_not_default_to_user(self):
        db = Mock()
        for data in ([], [{'role': 'unknown'}]):
            db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = data
            with self.assertRaises(HTTPException) as error:
                roles.get_user_access(db, 'id')
            self.assertEqual(error.exception.status_code, 403)

    def test_login_and_signup_do_not_change_database_client_session(self):
        for endpoint in ('login', 'signup'):
            database, auth_client = Mock(), Mock()
            response = SimpleNamespace(user=SimpleNamespace(id='id', email='test@example.com', user_metadata={'name': 'Test'}), session=SimpleNamespace(access_token='token'))
            auth_client.auth.sign_in_with_password.return_value = response
            auth_client.auth.sign_up.return_value = response
            with patch.object(api, 'supabase', database), patch.object(api, 'create_client', return_value=auth_client):
                if endpoint == 'login':
                    api.login(api.Auth(email='test@example.com', password='password'))
                    auth_client.auth.sign_in_with_password.assert_called_once()
                else:
                    api.signup(api.info(name='Test', email='test@example.com', password='password', role='manager'))
                    auth_client.auth.sign_up.assert_called_once()
                    database.table.return_value.insert.assert_called_once_with({'user_id': 'id', 'role': 'manager'})
            database.auth.sign_in_with_password.assert_not_called()
            database.auth.sign_up.assert_not_called()

    def test_signup_rejects_invalid_role_before_creating_account(self):
        with self.assertRaises(ValidationError):
            api.info(name='Test', email='test@example.com', password='password', role='Manager')
