from django.test import TestCase
from rest_framework.test import APIClient

class SalarySimulationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_simulate_foizli(self):
        res = self.client.post('/employee/salary/simulate/', {
            'type': 'foizli',
            'params': {'foiz': 5},
            'metrics': {'ordersTotal': 10000000}
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['calculated_amount'], 500000)

    def test_simulate_fiksa_foiz(self):
        res = self.client.post('/employee/salary/simulate/', {
            'type': 'fiksa_foiz',
            'params': {'baza_summa': 2000000, 'qoshimcha_foiz': 3},
            'metrics': {'ordersTotal': 10000000}
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['calculated_amount'], 2300000)

    def test_simulate_soatlik(self):
        res = self.client.post('/employee/salary/simulate/', {
            'type': 'soatlik',
            'params': {'stavka': 25000},
            'metrics': {'hoursWorked': 160}
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['calculated_amount'], 4000000)
