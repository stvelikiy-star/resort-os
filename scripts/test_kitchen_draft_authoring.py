"""Exercise real route authorization and recipe versioning without a live hotel."""
import json
import unittest
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from services.api.app import kitchen, kitchen_menu_management as menu


class DraftAuthoringTests(unittest.TestCase):
    def setUp(self):
        self.pid, self.item_id = uuid.uuid4(), uuid.uuid4()
        self.user = {"id": str(uuid.uuid4()), "role": "COOK"}
        self.row = {"id": self.item_id, "code": "TEST", "category": "MAIN", "nameRu": "Draft",
                    "nameKg": "Draft", "nameKz": "Draft", "nameEn": "Draft", "priceKgs": 0,
                    "isActive": False, "isDraft": True, "sortOrder": 0, "recipe": None}
        self.conn = SimpleNamespace(fetchrow=AsyncMock(side_effect=lambda *args: self.row),
                                    fetch=AsyncMock(return_value=[self.row]), execute=AsyncMock())
        @asynccontextmanager
        async def context():
            yield self.conn
        self.conn.transaction = context
        app = FastAPI()
        app.state.db = SimpleNamespace(acquire=context)
        app.include_router(menu.router)
        app.include_router(kitchen.admin_router)
        for dependency in (menu.draft_create_access, kitchen._waiter_menu_base):
            app.dependency_overrides[dependency] = lambda: self.user
        self.client = TestClient(app)
        self.patchers = [patch.object(menu, '_property_id', AsyncMock(return_value=self.pid)),
                         patch.object(kitchen, 'property_id', AsyncMock(return_value=self.pid))]
        for item in self.patchers:
            item.start()
            self.addCleanup(item.stop)
        self.path = '/api/v1/kitchen/menu/' + str(self.item_id)
        self.recipe = {"expected_version": 0, "status": "DRAFT", "is_sample": True,
                       "ingredients": [{"name": "Rice", "unit": "KG", "quantity_per_portion": "0.1"}]}

    def test_cook_edits_draft_with_property_lock_and_audit(self):
        result = self.client.patch(self.path, json={"name_ru": "Draft"})
        self.assertEqual(result.status_code, 200, result.text)
        sql, item_id, pid = self.conn.fetchrow.call_args_list[0].args
        self.assertIn('FOR UPDATE', sql)
        self.assertEqual((item_id, pid), (self.item_id, self.pid))
        self.assertIn('UPDATE_MENU_ITEM', self.conn.execute.call_args.args)

    def test_cook_cannot_change_price_publish_or_edit_active_dish(self):
        for changes in ({"price_kgs": 0}, {"is_active": True}, {"is_draft": False}):
            self.assertEqual(self.client.patch(self.path, json=changes).status_code, 403)
        self.row['isActive'] = True
        self.assertEqual(self.client.patch(self.path, json={"name_ru": "Changed"}).status_code, 403)
        self.conn.execute.assert_not_called()

    def test_module_grant_cannot_bypass_author_role(self):
        for role in ('WAITER', 'RECEPTION', 'STORE_STAFF'):
            self.user['role'] = role
            self.assertEqual(self.client.patch(self.path, json={"name_ru": "Changed"}).status_code, 403)
            self.assertEqual(self.client.put(self.path+'/recipe', json=self.recipe).status_code, 403)
            self.assertEqual(self.client.get('/api/v1/kitchen/menu').status_code, 200 if role == 'WAITER' else 403)
        self.conn.fetchrow.assert_not_called()

    def test_cook_draft_recipe_version_conflict_and_approval_denial(self):
        result = self.client.put(self.path+'/recipe', json=self.recipe)
        self.assertEqual(result.status_code, 200, result.text)
        saved = result.json()['recipe']
        self.assertEqual((saved['version'], saved['status']), (1, 'DRAFT'))
        self.row['recipe'] = json.dumps(saved)
        self.assertEqual(self.client.put(self.path+'/recipe', json=self.recipe).status_code, 409)
        self.assertEqual(self.client.put(self.path+'/recipe', json={**self.recipe, 'status':'APPROVED'}).status_code, 403)
        self.row['recipe'] = {**saved, 'status':'APPROVED'}
        self.assertEqual(self.client.put(self.path+'/recipe', json={**self.recipe, 'expected_version':1}).status_code, 403)

    def test_management_keeps_publication_authority(self):
        for role in ('OWNER', 'MANAGER'):
            self.user['role'] = role
            self.assertEqual(self.client.patch(self.path, json={'is_active':True,'is_draft':False}).status_code, 200)
            self.assertEqual(self.client.put(self.path+'/recipe', json={**self.recipe,'status':'APPROVED'}).status_code, 200)

    def test_list_scopes_cook_drafts_waiter_approved_only_and_owner_all(self):
        for role in ('COOK', 'OWNER', 'WAITER'):
            self.user['role'] = role
            result = self.client.get('/api/v1/kitchen/menu')
            self.assertEqual(result.status_code, 200, result.text)
            sql, pid, cook_draft_bypass, waiter_approved_bypass = self.conn.fetch.call_args.args
            self.assertEqual(pid, self.pid)
            self.assertEqual(cook_draft_bypass, role != 'COOK')
            self.assertEqual(waiter_approved_bypass, role != 'WAITER')
            self.assertIn('"isDraft"=true AND "isActive"=false', sql)
            self.assertIn('"isActive"=true AND "isDraft"=false', sql)
            if role == 'WAITER':
                self.assertNotIn('recipe', result.json()['items'][0])
            else:
                self.assertIn('recipe', result.json()['items'][0])


if __name__ == '__main__':
    unittest.main()
