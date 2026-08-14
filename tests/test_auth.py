import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.employee.models import Employee, Role, RoleModulePermission
from apps.sozlamalar.models import Branch

class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = Branch.objects.create(name="Bahor Cafe", city="Farg'ona")
        self.role = Role.objects.create(name="ADMIN", salary_type="fixed", salary_amount=5000000)
        self.user = User.objects.create_user(username="998774578407", password="testpassword123")
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test Admin",
            phone="998774578407",
            role=self.role,
            branch=self.branch
        )
        self.employee.set_pin("1447")

    def test_password_login_success(self):
        res = self.client.post('/employee/auth/login/', {
            'phone': '998774578407',
            'password': 'testpassword123'
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)
        self.assertEqual(res.data['user']['name'], 'Test Admin')

    def test_pin_login_success(self):
        res = self.client.post('/employee/auth/pin-login/', {
            'phone': '998774578407',
            'quick_pin': '1447'
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)

    def test_pin_login_wrong_pin(self):
        res = self.client.post('/employee/auth/pin-login/', {
            'phone': '998774578407',
            'quick_pin': '0000'
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_set_pin(self):
        res = self.client.post('/employee/auth/set-pin/', {
            'employee_id': self.employee.id,
            'quick_pin': '9999',
            'confirm_pin': '9999'
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_pin('9999'))
