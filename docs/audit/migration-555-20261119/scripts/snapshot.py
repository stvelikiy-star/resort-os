"""Hash each original field by primary key. Audit FK orphans including composite keys."""
import asyncio, hashlib, json, sys
from pathlib import Path
import asyncpg
def quote(name):
    return '"' + name.replace('"','""') + '"'
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
async def run(label,port,db):
    assert port in ('55431','55432') and db in ('marina_fixture','rollback','clean_new')
    c=await asyncpg.connect(f'postgresql://audit@127.0.0.1:{port}/{db}')
    result={'tables':{},'fk':{},'migrations':[]}
    tables=await c.fetch("select tablename from pg_tables where schemaname='public' order by 1")
    for name, in tables:
        table=quote(name)
        keys=await c.fetchval("""select array_agg(a.attname order by k.ord) from pg_index i
          cross join lateral unnest(i.indkey) with ordinality k(num,ord)
          join pg_attribute a on a.attrelid=i.indrelid and a.attnum=k.num
          where i.indrelid=$1::text::regclass and i.indisprimary""",table)
        rows=await c.fetch(f'select to_jsonb(t)::text from {table} t')
        assert not rows or keys, name
        contents={}
        for raw, in rows:
            row=json.loads(raw)
            key='|'.join(str(row[k]) for k in keys)
            contents[key]={n:digest(v) for n,v in row.items()}
        result['tables'][name]=contents
    fks=await c.fetch("""select conname, conrelid::regclass::text child, confrelid::regclass::text parent,
      array(select attname from unnest(conkey) with ordinality k(x,n) join pg_attribute on attnum=x and attrelid=conrelid order by n) ck,
      array(select attname from unnest(confkey) with ordinality k(x,n) join pg_attribute on attnum=x and attrelid=confrelid order by n) pk
      from pg_constraint where contype='f' and connamespace='public'::regnamespace""")
    for fk in fks:
        pairs=list(zip(map(quote,fk['ck']),map(quote,fk['pk'])))
        nonnull=' and '.join(f'c.{a} is not null' for a,b in pairs)
        match=' and '.join(f'p.{b}=c.{a}' for a,b in pairs)
        result['fk'][fk['conname']]=await c.fetchval(f"select count(*) from {fk['child']} c where {nonnull} and not exists(select 1 from {fk['parent']} p where {match})")
    result['migrations']=[dict(r) for r in await c.fetch("""select migration_name, checksum, extract(epoch from finished_at-started_at)::float seconds from _prisma_migrations order by started_at""")]
    result['amounts']={}
    for name,col in [('reservations','totalKgs'),('payments','amountKgs'),('kitchen_orders','totalKgs'),('guest_folio_charges','amountKgs'),('kitchen_order_items','lineTotalKgs')]:
        result['amounts'][name]=await c.fetchval(f'select coalesce(sum({quote(col)}),0) from {quote(name)}')
    Path('evidence/'+label+'.json').write_text(json.dumps(result,indent=1,sort_keys=True))
    await c.close()
asyncio.run(run(*sys.argv[1:]))
