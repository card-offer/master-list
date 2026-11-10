#!/usr/bin/env python3
"""Check-only validation of the published tree. Run from the repository root:

    python tools/validate.py

Checks: every file against its JSON schema, card and merchant references, every offer has a
source_url and an end_date, offers past their end_date are reported as warnings, and no em dash in any JSON file.
Exits non-zero on any failure."""
import json,os,sys,datetime
from jsonschema import Draft202012Validator,FormatChecker
from referencing import Registry,Resource
ROOT=sys.argv[1] if len(sys.argv)>1 else '.'
def J(p): return json.load(open(os.path.join(ROOT,p),encoding='utf-8'))
reg=Registry()
for f in os.listdir(os.path.join(ROOT,'schema')):
    s=J('schema/'+f); reg=reg.with_resource(s['$id'],Resource.from_contents(s))
def V(name): return Draft202012Validator(J('schema/'+name),registry=reg,format_checker=FormatChecker())
errs=[]; warns=[]
def add(where,msg): errs.append(f'{where}: {msg}')
countries=[d for d in ('my','sg') if os.path.isdir(os.path.join(ROOT,d))]
cards=set(); merchants=set(); offers=[]
for cc in countries:
    for n,s in [('cards','cards-file'),('offers','offers-file'),('merchants','merchants-file'),('issuers','issuers-file')]:
        data=J(f'{cc}/{n}.json')
        for e in V(s+'.schema.json').iter_errors(data): add(f'{cc}/{n}.json {e.json_path}',e.message[:200])
        if n=='cards': cards|={c['id'] for c in data['items']}
        if n=='merchants': merchants|={m['id'] for m in data['items']}
        if n=='offers': offers+=data['items']
    for f in os.listdir(os.path.join(ROOT,cc,'index')):
        for e in V('index.schema.json').iter_errors(J(f'{cc}/index/{f}')): add(f'{cc}/index/{f} {e.json_path}',e.message[:200])
if os.path.isdir(os.path.join(ROOT,'global')):
    for f in os.listdir(os.path.join(ROOT,'global')):
        for e in V('index.schema.json').iter_errors(J('global/'+f)): add('global/'+f,e.message[:200])
today=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date()
for o in offers:
    if not o.get('source_url'): add(o['id'],'missing source_url')
    if not o.get('end_date'): add(o['id'],'missing end_date')
    elif datetime.date.fromisoformat(o['end_date'])<today: warns.append(f"{o['id']}: past end_date {o['end_date']} (prune it)")
    if o.get('start_date') and o.get('end_date') and o['start_date']>o['end_date']: add(o['id'],'start_date after end_date')
    if not o.get('start_date') and not o.get('start_date_null_reason'): add(o['id'],'start_date null without start_date_null_reason')
    if o.get('terms_url') is None and not o.get('terms_url_null_reason'): add(o['id'],'terms_url null without terms_url_null_reason')
    for cid in o.get('eligible_card_ids',[]):
        if cid not in cards: add(o['id'],f'unknown card id {cid}')
    for mid in o.get('merchant_ids',[]):
        if mid not in merchants: add(o['id'],f'unknown merchant id {mid}')
for dp,_,fs in os.walk(ROOT):
    if '.git' in dp: continue
    for f in fs:
        if f.endswith(('.json','.md','.yml','.yaml')) and '\u2014' in open(os.path.join(dp,f),encoding='utf-8').read(): add(os.path.join(dp,f),'contains an em dash')
for w in warns[:50]: print('warning',w)
for e in errs[:50]: print(e)
print(f'offers {len(offers)}, cards {len(cards)}, merchants {len(merchants)}, errors {len(errs)}')
sys.exit(1 if errs else 0)
