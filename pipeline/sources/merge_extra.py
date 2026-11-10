"""Merge the source-sweep adapter output into the pipeline's working files. Idempotent.
Run after build_cards.py and build_offers.py, before publish.py, inside: flock /workspace/cc-master/.build.lock
 - raw/extra_cards/cards.json  -> appended to raw/cards_built.json (by id); issuers added to pipeline/issuers_config.json
 - raw/extra_offers/*.json     -> appended to raw/offers_built.json, except:
     * offers with no end_date (held back: raw/extra_offers_held_back.json)
     * offers already present from the main crawl (same source_url and title, or same issuer+title)
 Keys are limited to the properties the current offer schema allows, so the publish validation keeps passing
 while the schema is being extended (start_date, end_date, terms clauses etc. pass through once the schema has them).
 Full records stay in raw/extra_offers/ for the date/T&C worker."""
import re,json,glob,os,sys,re,datetime
SCH='master-list/schema/offer.schema.json'
allowed=set(json.load(open(SCH))['properties'])|{'_merchant_name'}
csch=json.load(open('master-list/schema/card.schema.json')); callowed=set(csch['properties'])|{'_merchant_name','network_source'}
MARK='raw/extra_merged_ids.json'
prev=json.load(open(MARK)) if os.path.exists(MARK) else {'offers':[],'cards':[]}
# ---- cards
cards=json.load(open('raw/cards_built.json'))
cards=[c for c in cards if c['id'] not in set(prev['cards'])]
ex=json.load(open('raw/extra_cards/cards.json')) if os.path.exists('raw/extra_cards/cards.json') else {'issuers':[],'cards':[]}
have={c['id'] for c in cards}; addc=[]
for c in ex['cards']:
    if c['id'] in have: continue
    c={k:v for k,v in c.items() if k in callowed}
    cards.append(c); addc.append(c['id']); have.add(c['id'])
cfg=json.load(open('pipeline/issuers_config.json')); ids={i['id'] for i in cfg}; addi=[]
for i in ex['issuers']:
    if i['id'] not in ids: cfg.append(i); addi.append(i['id'])
# ---- offers
offers=json.load(open('raw/offers_built.json'))
offers=[o for o in offers if o['id'] not in set(prev['offers'])]
key1={(o['source_url'],o['title'].lower()) for o in offers}; key2={(o['issuer_id'],o['title'].lower()) for o in offers}
srcs={o['source_url'] for o in offers}
held=[]; XO=set(); dup=0; seen=set(); cardids={c['id'] for c in cards}
for f in sorted(glob.glob('raw/extra_offers/*.json')):
    for o in json.load(open(f))['offers']:
        k=(o['issuer_id'],o['title'].lower())
        if (o['source_url'],o['title'].lower()) in key1 or k in key2 or k in seen: dup+=1; continue
        # a detail page already crawled by the main pipeline: keep the main record
        if o['source_url'] in srcs and not o['source_url'].endswith(('index.html','.page','/promotions/','card-promotion')): dup+=1; continue
        seen.add(k)
        if not o.get('end_date'):
            o['end_date_status']='evergreen'
        o['eligible_card_ids']=[c for c in o.get('eligible_card_ids') or [] if c in cardids]
        o['eligibility']['card_ids']=[c for c in o['eligibility'].get('card_ids',[]) if c in cardids]
        if o['eligibility']['scope']=='card' and not o['eligibility']['card_ids']: o['eligibility']['scope']='issuer'
        r={k2:v for k2,v in o.items() if k2 in allowed}
        r['benefit']={k2:v for k2,v in o['benefit'].items()}
        r['_extra']=o
        offers.append(r); XO.add(id(r))
# unique source_url per offer (publish.py joins dates/T&C by source_url): listing-hub offers get a #fragment
from collections import Counter
cnt=Counter(o['source_url'] for o in offers)
import unicodedata
def sl(x): return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().lower()).strip('-')[:60]
ENRP='raw/terms_enriched.json'; ENR=json.load(open(ENRP)) if os.path.exists(ENRP) else {}
ENR={k:v for k,v in ENR.items() if v.get('origin')!='source_sweep'}
for r in offers:
    o=r.pop('_extra',None)
    if o is None: continue
    if cnt[r['source_url']]>1 or r['source_url'] in ENR:
        r['source_url']=r['source_url'].split('#')[0]+'#'+sl(r['title'])
    rec={'source_url':r['source_url'],'origin':'source_sweep','adapter':o.get('adapter'),'page_mode':'adapter'}
    v=o.get('validity') or {}
    if o.get('end_date'):
        rec['period']={'valid_from':o.get('start_date'),'valid_until':o['end_date'],'text':(v.get('text') or '')[:300],'start_basis':'stated' if o.get('start_date') else 'not_stated',
                       'source_url':o.get('dates_source_url') or r['source_url'].split('#')[0],'source_kind':'terms' if (o.get('terms') and o.get('dates_source_url')==o['terms'].get('url')) else 'page'}
    t=o.get('terms')
    if t and t.get('clauses'):
        rec['terms']={'url':t['url'],'fetched_at':t['fetched_at'],'kind':'page_section' if t.get('kind') in ('page_section','listing_json_terms_html') else (t.get('kind') or 'html'),'hash':t['hash'],'clauses':t['clauses']}
    if o.get('min_spend'): rec['min_spend']={'text':o['min_spend']['text'],'source_url':o['min_spend'].get('source_url') or (t or {}).get('url') or r['source_url'].split('#')[0]}
    if o.get('cap'): rec['cap']={'text':o['cap']['text'],'source_url':o['cap'].get('source_url') or (t or {}).get('url') or r['source_url'].split('#')[0]}
    r['sources'][0]['kind']='issuer_promotion_page'
    KM={'issuer_listing_data_json':'issuer_promotion_listing','issuer_promotion_listing':'issuer_promotion_listing'}
    OK={'issuer_product_page','issuer_listing','issuer_promotion_page','issuer_promotion_listing','network_offer_page','merchant_page','issuer_terms_document'}
    for x in r['sources'][1:]:
        x['kind']=KM.get(x['kind'],x['kind'])
        if x['kind'] not in OK: x['kind']='issuer_terms_document' if re.search(r'(?i)\.pdf|tnc|terms',x['url']) else 'issuer_promotion_page'
    ENR[r['source_url']]=rec
# unique ids
c={}
for o in offers:
    c[o['id']]=c.get(o['id'],0)+1
    if c[o['id']]>1 and id(o) in XO: o['id']+=f"-{c[o['id']]}"
added=[o['id'] for o in offers if id(o) in XO]
dry='--dry' in sys.argv
if not dry:
    json.dump(cards,open('raw/cards_built.json','w'),indent=1,ensure_ascii=False)
    json.dump(offers,open('raw/offers_built.json','w'),indent=1,ensure_ascii=False)
    json.dump(cfg,open('pipeline/issuers_config.json','w'),indent=1,ensure_ascii=False)
    json.dump(held,open('raw/extra_offers_held_back.json','w'),indent=1,ensure_ascii=False)
    json.dump(ENR,open(ENRP,'w'),indent=1,ensure_ascii=False)
    json.dump({'offers':added,'cards':addc,'issuers':addi,'merged_at':datetime.datetime.now().isoformat(timespec='seconds')},open(MARK,'w'),indent=1)
print(json.dumps({'cards_added':len(addc),'issuers_added':addi,'offers_added':len(added),'held_back_no_end_date':len(held),'duplicates_skipped':dup,'dry':dry}))
