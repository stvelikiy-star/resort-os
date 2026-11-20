import json,csv
from pathlib import Path
def read(n): return json.loads(Path(f'evidence/{n}.json').read_text())
a,b=read('before'),read('after')
s={'clone_exact':read('clone')==a,'rollback_exact':read('rollback')==a,'lost_tables':sorted(a['tables'].keys()-b['tables'].keys()),'missing_rows':[],'changed_original_fields':[],'new_tables':sorted(b['tables'].keys()-a['tables'].keys()),'migration_seconds':sum(r['seconds'] for r in b['migrations'][24:]),'fk_orphans':sum(b['fk'].values()),'amounts_equal':a['amounts']==b['amounts']}
for t,rows in a['tables'].items():
 for key,row in rows.items():
    target=b['tables'].get(t,{}).get(key)
    if target is None: s['missing_rows'].append([t,key]);continue
    for col,val in row.items():
        if target.get(col)!=val:s['changed_original_fields'].append([t,key,col])
with open('evidence/tables.csv','w') as f:
 out=csv.writer(f);out.writerow(['table','old_rows','new_rows'])
 for t in sorted(b['tables']):out.writerow([t,len(a['tables'][t]) if t in a['tables'] else 'absent',len(b['tables'][t])])
p,q=[{(m,k) for k,d in read('openapi-'+v)['paths'].items() for m in d} for v in ['old','new']]
s.update(old_operations=len(p),new_operations=len(q),lost_operations=sorted(p-q),added_operations=sorted(q-p))
rows=list(csv.DictReader(open('evidence/rights.csv')))
index={(r['version'],r['role'],r['method'],r['path']):r['http_or_coverage'] for r in rows}
with open('evidence/rights-changes.csv','w') as f:
 w=csv.writer(f);w.writerow(['role','method','path','old_http','new_http'])
 for (version,role,method,path),old in index.items():
    new=index.get(('new',role,method,path),'')
    if version=='old' and old.isdigit() and new.isdigit() and old!=new:w.writerow([role,method,path,old,new])
Path('evidence/summary.json').write_text(json.dumps(s,indent=1))
