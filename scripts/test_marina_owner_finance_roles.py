"""Actual OWNER routers must reject a custom FINANCE grant on any other role."""
import sys
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import auth, owner_expenses, owner_cash_reconciliation, owner_kitchen_management


class OwnerFinanceRoles(unittest.TestCase):
    def test_custom_finance_module_cannot_promote_any_other_staff_role(self):
        app = FastAPI()
        for module in (owner_expenses, owner_cash_reconciliation, owner_kitchen_management):
            app.include_router(module.router)
        user = {'role': '', 'id': '00000000-0000-4000-8000-000000000001',
                'module_permissions_custom': True, 'module_permissions': ['FINANCE']}
        app.dependency_overrides[auth.current_user] = lambda: user
        # Deliberately no app.state.db: an authorization regression fails before
        # any database read/write instead of accidentally accessing finance.
        client = TestClient(app)
        base = '/api/v1/admin/finance/owner'
        for role in ('MANAGER', 'RECEPTION', 'AGENT', 'MAID', 'TECHNICIAN', 'COOK',
                     'WAITER', 'STORE_STAFF', 'DINING_STAFF', 'CONTENT_MANAGER', 'BEACH_PARTNER'):
            user['role'] = role
            for path in ('/expenses', '/recorded-cash-movements', '/kitchen-operations'):
                with self.subTest(role=role, path=path):
                    result = client.get(base + path, params={'from_date': '2026-11-15', 'to_date': '2026-11-15'})
                    self.assertEqual(result.status_code, 403, result.text)
            writes = [
                ('/expenses', {'id':'00000000-0000-4000-8000-000000000002', 'expense_date':'2026-11-15', 'category':'OTHER', 'title':'Synthetic', 'amount_kgs':100}),
                ('/expenses/00000000-0000-4000-8000-000000000002/settlements', {'id':'00000000-0000-4000-8000-000000000003', 'amount_kgs':10, 'paid_on':'2026-11-15', 'method':'CASH'}),
                ('/expenses/00000000-0000-4000-8000-000000000002/void', {'reason':'Synthetic duplicate'}),
            ]
            for path, body in writes:
                with self.subTest(role=role, method='POST', path=path):
                    self.assertEqual(client.post(base + path, json=body).status_code, 403)


if __name__ == '__main__':
    unittest.main()
