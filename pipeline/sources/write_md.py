"""Write worksheet/sources.md from worksheet/sources.csv and the published master list."""
import csv,json,collections,os,sys,re
sys.path[:0]=['scripts','scripts/sources']; import ws
R=list(csv.DictReader(open('worksheet/sources.csv')))
st=collections.Counter(r['status'] for r in R)
banks=collections.defaultdict(set)
for r in R:
    if r['page_type']!='network_portal': banks[r['country']].add(r['bank'])
NOTCC={'MBSB Bank','GXBank','AEON Bank','Kuwait Finance House'}
UNCONF={'Agrobank','Diners Club Malaysia','American Express MY','Citibank MY','Co-opbank Pertama'}
pub={}
for cc in ('my','sg'):
    f=f'master-list/{cc}/offers.json'
    if os.path.exists(f): pub[cc]=collections.Counter(o['issuer_id'] for o in json.load(open(f))['items'])
base={}
for l in open('raw/sources/baseline_counts.txt'):
    m=re.match(r"(my|sg) \d+ (\{.*\})",l)
    if m: base[m.group(1)]=eval(m.group(2))
L=[]; A=L.append
A('# Credit card source worksheet: Malaysia and Singapore'); A('')
A(f'Generated {ws.now()} (Asia/Kuala_Lumpur). Rows: {len(R)}; done {st["done"]}, blocked {st["blocked"]}, to do {st["to do"]}, in progress {st["in progress"]}.'); A('')
A('Official bank, network and merchant pages only. Public pages only; no sign-in, forms or contact. Polite crawl, cached under raw/cache/.'); A('')
for cc in ('MY','SG'):
    iss=sorted(b for b in banks[cc] if b not in NOTCC|UNCONF)
    A(f'## {cc}: {len(iss)} credit card issuers'); A('')
    A('Issuers: '+', '.join(iss)+'.'); A('')
    nc=sorted(b for b in banks[cc] if b in NOTCC)
    if nc: A('Checked, not credit card issuers on their official site: '+', '.join(nc)+'.'); A('')
    uc=sorted(b for b in banks[cc] if b in UNCONF)
    if uc: A('Listed but not confirmed (site unreachable or no issuer catalogue found): '+', '.join(uc)+'.'); A('')
    A('| bank | page type | status | cards | offers | url | notes |'); A('|---|---|---|---|---|---|---|')
    for r in sorted([r for r in R if r['country']==cc],key=lambda r:(r['page_type']=='network_portal',r['bank'],r['page_type'])):
        n=r['notes_blockers'].replace('|','/')[:160]
        A(f"| {r['bank']} | {r['page_type']} | {r['status']} | {r['cards_found']} | {r['offers_found']} | {r['source_url']} | {n} |")
    A('')
A('## Published offers per issuer (before this sweep, after)'); A('')
A('| issuer | before | after |'); A('|---|---|---|')
for cc in ('my','sg'):
    for i in sorted(set(base.get(cc,{}))|set(pub.get(cc,{}))):
        A(f"| {i} | {base.get(cc,{}).get(i,0)} | {pub.get(cc,{}).get(i,0)} |")
A('')
A('## Blocked rows'); A('')
for r in R:
    if r['status']=='blocked': A(f"- {r['country']} {r['bank']} ({r['page_type']}): {r['source_url']} : {r['notes_blockers']}")
txt='\n'.join(L).replace('\u2014',',').replace('\u2013','-')
open('worksheet/sources.md.tmp','w').write(txt+'\n'); os.replace('worksheet/sources.md.tmp','worksheet/sources.md')
print('wrote worksheet/sources.md',len(L),'lines')
