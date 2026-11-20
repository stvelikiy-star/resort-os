"""Search both complete tracked trees; list file/line evidence, including negative guards and docs."""
import csv,re,subprocess
from pathlib import Path
patterns={'night_shift':r'night.audit|ночн\w* аудит|закрыти\w* смен|shift.clos|close.shift','fiscal':r'фискал|фискаль|электронн\w* счет|\bэсф\b|fiscali|e-invoic','foreign_guests':r'иностранн\w* гост|foreign.{0,12}(guest|registration)|migration.registration','payment':r'mkassa|payment.provider|payment.gateway|эквайринг','accounting_export':r'export\.xlsx|accounting.export|бухгалтерск\w* экспорт|1[cс]:','channels':r'channel.manager|channel.sync|OTA.sync|booking\.com|channel.outbound','loyalty':r'loyalty|лояльност|bonus.points'}
brands=r'three[ _-]?crowns|три корон|үч тааж|3koron|ak[ _-]?bermet|ак[ _-]?бермет|aska[ _-]?tash|аска[ _-]?таш'
for v in ['old','new']:
    files=subprocess.check_output(['git','-C',v,'ls-files','-z']).decode().split('\0')
    with open(f'evidence/catalog-{v}.csv','w') as f,open(f'evidence/brand-{v}.csv','w') as b:
        writer=csv.writer(f); brand=csv.writer(b)
        writer.writerow(['topic','path','line','match']);brand.writerow(['path','line','match'])
        for file in filter(None,files):
            p=Path(v,file)
            if not p.is_file(): continue
            try: lines=p.read_text().splitlines()
            except UnicodeDecodeError: continue
            for n,line in enumerate(lines,1):
                for key,regex in patterns.items():
                    m=re.search(regex,line,re.I)
                    if m: writer.writerow([key,file,n,m.group()])
                if file.startswith(('apps/admin/','apps/staff/','apps/mobile/','apps/web/','services/api/')):
                    m=re.search(brands,line,re.I)
                    if m:brand.writerow([file,n,m.group()])
