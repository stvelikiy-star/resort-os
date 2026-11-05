"""Exercise the production seasonal-pricing function with controlled rate rows."""
import ast
import asyncio
from datetime import date, timedelta
from pathlib import Path
from typing import Any
source = Path(__file__).resolve().parents[1] / 'services/api/app/main.py'
tree = ast.parse(source.read_text())
functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in {'nights_between', 'price_room_type'}]
ns = dict(date=date, timedelta=timedelta, Any=Any, RATE_PLAN_CODE='DIRECT_2026_27')
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), ns)
class Connection:
    def __init__(self, rows): self.rows = rows
    async def fetch(self, *_): return self.rows

def rate(start, end, price, label='season', status='OPEN'):
    return dict(validFrom=date.fromisoformat(start), validTo=date.fromisoformat(end), priceKgs=price, mealIncluded='NONE', saleStatus=status, label=label)

async def main():
    cases = [
        ('one night', [rate('2027-08-01','2027-08-31',5000)], '2027-08-01','2027-08-02',5000,None),
        ('future December', [rate('2027-12-01','2027-12-31',3000)], '2027-12-04','2027-12-07',9000,None),
        ('season boundary', [rate('2027-07-01','2027-07-31',3000),rate('2027-08-01','2027-08-31',5000)], '2027-07-31','2027-08-03',13000,None),
        ('checkout excluded', [rate('2027-07-01','2027-07-31',3000)], '2027-07-31','2027-08-01',3000,None),
        ('missing night', [rate('2027-08-01','2027-08-01',5000)], '2027-08-01','2027-08-03',None,'RATE_MISSING'),
        ('closed', [rate('2027-08-01','2027-08-31',5000,status='CLOSED')], '2027-08-01','2027-08-02',None,'RATE_CLOSED'),
        ('confirmation', [rate('2027-08-01','2027-08-31',5000,status='CONFIRM_REQUIRED')], '2027-08-01','2027-08-02',None,'RATE_REQUIRES_CONFIRMATION'),
        ('zero', [rate('2027-08-01','2027-08-31',0)], '2027-08-01','2027-08-02',None,'RATE_CLOSED'),
        ('overlap', [rate('2027-08-01','2027-08-31',5000),rate('2027-08-01','2027-08-02',9000)], '2027-08-01','2027-08-02',None,'RATE_OVERLAP'),
        ('invalid', [], '2027-08-02','2027-08-01',None,'INVALID_DATE_RANGE'),
        ('leap day', [rate('2028-02-01','2028-03-31',4000)], '2028-02-28','2028-03-01',8000,None),
        ('year boundary', [rate('2027-12-01','2027-12-31',3000),rate('2028-01-01','2028-01-31',4000)], '2027-12-31','2028-01-02',7000,None),
    ]
    for label, rows, start, end, total, reason in cases:
        result = await ns['price_room_type'](Connection(rows), 'room', date.fromisoformat(start), date.fromisoformat(end))
        assert result['total_kgs'] == total and result['reason'] == reason, (label,result)
        print('PASS',label)
asyncio.run(main())
