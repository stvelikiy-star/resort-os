"""Local isolated PostgreSQL E2E: supplier return -> stock debit + credit note.

Never sends real supplier payments. No remote DB, hotel or production writes.
"""
import asyncio
import os
import uuid
from decimal import Decimal
import asyncpg
import httpx


def require(r,status,label):
    assert r.status_code==status,(label,r.status_code,r.text)
    return r.json()


async def login(client,username,password,role):
    require(await client.post('/api/v1/auth/login',
            json={'username':username,'password':password}),200,'login '+role)
    me=require(await client.get('/api/v1/auth/me'),200,'me '+role)
    assert me['role']==role
    return me


async def main():
    if os.getenv('ALLOW_SUPPLIER_DOCUMENT_TEST_WRITES')!='1':
        raise RuntimeError('Supplier return test requires explicit isolated opt-in')
    url=os.environ['DATABASE_URL'].split('?',1)[0]
    base=os.getenv('CORE_API_URL','http://127.0.0.1:8000')
    if not ('@localhost:' in url or '@127.0.0.1:' in url):
        raise RuntimeError('Nonlocal DB refused')
    if not base.startswith('http://127.0.0.1:'):
        raise RuntimeError('Nonlocal API refused')
    db=await asyncpg.connect(url)
    item_id=doc_id=request_id=receipt_id=return_id=None
    pid=None
    try:
        async with httpx.AsyncClient(base_url=base,timeout=35) as owner, \
                   httpx.AsyncClient(base_url=base,timeout=35) as store:
            me=await login(owner,os.environ['BOOTSTRAP_OWNER_USERNAME'],
                           os.environ['BOOTSTRAP_OWNER_PASSWORD'],'OWNER')
            await login(store,os.environ['PROC_STORE_USERNAME'],
                        os.environ['PROC_STORE_PASSWORD'],'STORE_STAFF')
            pid=await db.fetchval('SELECT id FROM properties WHERE code=$1',me['property_code'])
            before_payments=await db.fetchval('SELECT COUNT(*) FROM payments')
            before_expenses=await db.fetchval(
                'SELECT COUNT(*) FROM owner_expenses WHERE "propertyId"=$1',pid)
            today=(await db.fetchval(
                'SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1',pid)).isoformat()
            token=uuid.uuid4().hex[:10]
            item_id=require(await owner.post('/api/v1/kitchen/stock/items',json={
                'name':'Supplier return E2E '+token,'unit':'KG',
                'cost_per_unit_kgs':'100','is_sample':False}),201,'item')['id']
            doc_id=str(uuid.uuid4());line_id=str(uuid.uuid4())
            require(await owner.post('/api/v1/admin/finance/owner/supplier-documents',json={
                'id':doc_id,'supplier_name':'E2E Supplier '+token,
                'document_reference':'INV-'+token,'document_date':today,
                'lines':[{'id':line_id,'stock_item_id':item_id,
                          'quantity':'5','unit_cost_kgs':'140'}]}),201,'invoice')
            request_id=str(uuid.uuid4())
            require(await owner.post('/api/v1/kitchen/procurement/requests',json={
                'request_id':request_id,'stock_item_id':item_id,
                'quantity':'5','service_date':today}),201,'request')
            require(await owner.post(
                '/api/v1/kitchen/procurement/requests/'+request_id+'/approve'),200,'approve')
            receipt_id=str(uuid.uuid4())
            require(await store.post(
                '/api/v1/kitchen/procurement/requests/'+request_id+'/receive',
                json={'receipt_id':receipt_id,'quantity':'5','document_line_id':line_id}),
                201,'atomic receipt')
            report_url='/api/v1/admin/finance/owner/kitchen-operations'
            report_params={'from_date':today,'to_date':today}
            require(await store.get(report_url,params=report_params),403,
                    'STORE denied OWNER kitchen financial reconciliation')
            before_report=require(await owner.get(report_url,params=report_params),
                                  200,'OWNER stock and supplier before credit')
            before_sources=before_report['source_reconciliation']['supplier_documents']
            before_stock=before_report['source_reconciliation']['inventory']
            before_credited=Decimal(before_sources['credit_notes_kgs'])
            before_outstanding=Decimal(before_sources['outstanding_payables_kgs'])
            before_return_cost=Decimal(
                before_report['real_supplier_return_stock_debit_kgs'])
            before_book=before_stock['real_book_inventory_value_kgs']
            assert before_report['source_reconciliation']['financial_truth']['recognized_profit_kgs'] is None
            assert before_sources['gross_obligations_kgs'] is not None
            source=require(await store.get('/api/v1/kitchen/procurement/supplier-lines'),200,'source list')
            assert source['payment_created'] is False
            assert any(x['id']==line_id and Decimal(x['remaining_quantity'])==0
                       for x in source['items'])
            deny=await store.post('/api/v1/admin/finance/owner/supplier-returns',
                json={'id':str(uuid.uuid4()),'document_id':doc_id,
                      'document_line_id':line_id,'quantity':'1',
                      'credit_reference':'CR-DENY','reason':'Staff not authorized'})
            require(deny,403,'store cannot credit supplier')
            return_id=str(uuid.uuid4())
            body={'id':return_id,'document_id':doc_id,'document_line_id':line_id,
                  'quantity':'2','credit_reference':'CREDIT-'+token,
                  'reason':'Rejected damaged goods'}
            attempts=await asyncio.gather(*[
                owner.post('/api/v1/admin/finance/owner/supplier-returns',json=body)
                for _ in range(8)])
            assert all(x.status_code==201 for x in attempts),[(x.status_code,x.text) for x in attempts]
            assert sum(not x.json()['already_processed'] for x in attempts)==1
            assert all(Decimal(x.json()['credit_amount_kgs'])==Decimal('280')
                       for x in attempts)
            require(await owner.post('/api/v1/admin/finance/owner/supplier-returns',
                json={**body,'quantity':'1'}),409,'same UUID changed payload')
            require(await owner.post('/api/v1/admin/finance/owner/supplier-returns',
                json={**body,'id':str(uuid.uuid4())}),409,'same credit reference')
            ledger=require(await owner.get('/api/v1/admin/finance/owner/supplier-returns'),
                           200,'return ledger')
            assert sum(x['id']==return_id for x in ledger['items'])==1
            invoice=require(await owner.get('/api/v1/admin/finance/owner/supplier-documents'),
                            200,'invoice after credit')
            row=next(x for x in invoice['items'] if x['id']==doc_id)
            assert Decimal(row['amount_kgs'])==Decimal('700')
            assert Decimal(row['credited_kgs'])==Decimal('280')
            assert Decimal(row['outstanding_kgs'])==Decimal('420')
            assert await db.fetchval(
                '''SELECT COUNT(*) FROM kitchen_supplier_returns
                   WHERE id=$1''',uuid.UUID(return_id))==1
            movement=await db.fetchrow(
                '''SELECT kind,quantity,"unitCostKgs" FROM kitchen_stock_movements
                   WHERE id=$1''',uuid.UUID(return_id))
            assert movement['kind']=='SUPPLIER_RETURN'
            assert movement['quantity']==Decimal('2')
            assert movement['unitCostKgs']==Decimal('140')
            stock=require(await owner.get('/api/v1/kitchen/stock'),200,'stock after return')
            entry=next(x for x in stock['items'] if x['id']==item_id)
            assert Decimal(entry['balance'])==Decimal('3')
            assert Decimal(entry['inventory_value_kgs'])==Decimal('420')
            after_report=require(await owner.get(report_url,params=report_params),
                                 200,'OWNER stock and supplier after return')
            after_sources=after_report['source_reconciliation']['supplier_documents']
            after_stock=after_report['source_reconciliation']['inventory']
            assert Decimal(after_sources['credit_notes_kgs'])-before_credited==Decimal('280')
            assert before_outstanding-Decimal(after_sources['outstanding_payables_kgs'])==Decimal('280')
            assert Decimal(after_report['real_supplier_return_stock_debit_kgs'])-before_return_cost==Decimal('280')
            if before_book is not None and after_stock['real_book_inventory_value_kgs'] is not None:
                assert Decimal(before_book)-Decimal(after_stock['real_book_inventory_value_kgs'])==Decimal('280')
            else:
                assert after_stock['valuation_status']=='RECONCILIATION_REQUIRED'
            assert after_report['procurement_exposure']['outstanding_supplier_payables_kgs']==after_sources['outstanding_payables_kgs']
            assert after_report['current_stock']['real_book_inventory_value_kgs']==after_stock['real_book_inventory_value_kgs']
            assert after_sources['return_credit_minus_stock_cost_kgs'] is not None
            assert after_report['source_reconciliation']['financial_truth']['recognized_profit_kgs'] is None
            summary=require(await owner.get('/api/v1/admin/finance/summary',
                                            params=report_params),200,'OWNER finance overview')
            owner_summary=summary['owner_supplier_stock_snapshot']
            assert owner_summary['supplier_documents']['outstanding_payables_kgs']==after_sources['outstanding_payables_kgs']
            assert owner_summary['inventory']['real_book_inventory_value_kgs']==after_stock['real_book_inventory_value_kgs']
            settle={'id':str(uuid.uuid4()),'amount_kgs':'420','paid_on':today,
                    'method':'BANK_TRANSFER','reference':'E2E-SETTLE-'+token}
            require(await owner.post(
                '/api/v1/admin/finance/owner/supplier-documents/'+doc_id+'/settlements',
                json=settle),201,'settle remaining')
            require(await owner.post(
                '/api/v1/admin/finance/owner/supplier-documents/'+doc_id+'/settlements',
                json={**settle,'id':str(uuid.uuid4()),'amount_kgs':'1'}),
                409,'overpay after credit denied')
            require(await owner.post('/api/v1/admin/finance/owner/supplier-returns',json={
                **body,'id':str(uuid.uuid4()),'credit_reference':'SECOND-'+token,
                'quantity':'1'}),409,'no credit beyond unpaid')
            invoice=require(await owner.get('/api/v1/admin/finance/owner/supplier-documents'),
                            200,'final payable')
            assert Decimal(next(x for x in invoice['items'] if x['id']==doc_id)['outstanding_kgs'])==0
            final_report=require(await owner.get(report_url,params=report_params),
                                 200,'OWNER after supplier settlement')
            final_balance=Decimal(final_report['source_reconciliation']['supplier_documents']['outstanding_payables_kgs'])
            assert Decimal(after_sources['outstanding_payables_kgs'])-final_balance==Decimal('420')
            assert final_report['source_reconciliation']['financial_truth']['is_recognized_profit_complete'] is False
            assert await db.fetchval('SELECT COUNT(*) FROM payments')==before_payments
            assert await db.fetchval(
                'SELECT COUNT(*) FROM owner_expenses WHERE "propertyId"=$1',pid)==before_expenses
            print('SUPPLIER_RETURN_POSTGRES_E2E_PASS: one debit, one credit, '
                  '8 retries, no over-return or overpay, no customer Payment')
    finally:
        if doc_id and pid:
            async with db.transaction():
                await db.execute(
                    'DELETE FROM kitchen_supplier_settlements WHERE "documentId"=$1',
                    uuid.UUID(doc_id))
                await db.execute(
                    'DELETE FROM kitchen_supplier_returns WHERE "documentId"=$1',
                    uuid.UUID(doc_id))
                if return_id:
                    await db.execute(
                        'DELETE FROM kitchen_stock_movements WHERE id=$1',uuid.UUID(return_id))
                await db.execute(
                    'DELETE FROM kitchen_supplier_receipt_links WHERE "documentLineId"=$1',
                    uuid.UUID(line_id))
                if receipt_id:
                    await db.execute(
                        'DELETE FROM kitchen_procurement_receipts WHERE id=$1',
                        uuid.UUID(receipt_id))
                    await db.execute(
                        'DELETE FROM kitchen_stock_movements WHERE id=$1',
                        uuid.UUID(receipt_id))
                if request_id:
                    await db.execute(
                        'DELETE FROM kitchen_procurement_requests WHERE id=$1',
                        uuid.UUID(request_id))
                await db.execute(
                    'DELETE FROM kitchen_supplier_document_lines WHERE "documentId"=$1',
                    uuid.UUID(doc_id))
                await db.execute(
                    'DELETE FROM kitchen_supplier_documents WHERE id=$1',
                    uuid.UUID(doc_id))
                if item_id:
                    await db.execute('DELETE FROM kitchen_stock_items WHERE id=$1',
                                     uuid.UUID(item_id))
        await db.close()


if __name__=='__main__':
    asyncio.run(main())
