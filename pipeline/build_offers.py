import sys,re,json,unicodedata; sys.path.insert(0,'pipeline')
from fetch import fetch; from extract import visible_text,title as ptitle,h1,meta,NET,networks_in; from links import links; from offer_extract import *
cards=json.load(open('raw/cards_built.json'))
iss_cfg={c['id']:c for c in json.load(open('pipeline/issuers_config.json'))}
cands=json.load(open('raw/offer_candidates.json'))
CCY={'MY':'MYR','SG':'SGD'}
def slug(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().replace('&',' and ').replace('+',' plus ')
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')[:80]
BRAND={'my-maybank':'maybank','my-cimb':'cimb','my-public-bank':'public bank|pb ','my-rhb':'rhb','my-hong-leong':'hong leong|hlb','my-ambank':'ambank','my-uob':'uob','my-ocbc':'ocbc','my-hsbc':'hsbc','my-standard-chartered':'standard chartered','my-alliance':'alliance','my-affin':'affin','my-aeon-credit':'aeon','my-bsn':'bsn','my-bank-islam':'bank islam','my-muamalat':'muamalat','my-al-rajhi':'al rajhi|alrajhi',
 'sg-dbs':'dbs','sg-posb':'posb','sg-ocbc':'ocbc','sg-uob':'uob','sg-citi':'citi','sg-standard-chartered':'standard chartered','sg-hsbc':'hsbc','sg-maybank':'maybank','sg-amex':'american express','sg-cimb':'cimb','sg-boc':'boc|bank of china'}
def norm(s): return re.sub(r'[^a-z0-9+ ]+',' ',s.lower().replace('\u2019',"'").replace('®','').replace('™','')).split()
def card_matches(iss,text):
    t=' '+' '.join(norm(text))+' '
    pool=[c for c in cards if c['issuer_id']==iss or (iss=='sg-dbs' and c['issuer_id']=='sg-posb')]
    hit=[]
    for c in pool:
        n=' '.join(w for w in norm(c['name']) if w not in ('credit','card','cards','the'))
        n=re.sub(r'\s+',' ',n).strip()
        if len(n)>6 and (' '+n+' ') in t: hit.append(c['id'])
    # drop ids whose name is a substring of a longer matched name
    names={c['id']:' '.join(norm(c['name'])) for c in pool}
    hit=[h for h in hit if not any(h!=o and names[h] in names[o] for o in hit)]
    return hit,pool
def eligibility(iss,text,title_):
    hit,pool=card_matches(iss,title_+'\n'+text[:6000])
    l=(title_+' '+text[:6000]).lower()
    brand=BRAND.get(iss,'')
    nets=[]
    for n,p in NET:
        if re.search(r'(%s)[\w\s/-]{0,25}(%s)[\w\s/-]{0,25}(credit )?cards?'%(brand,p),l) or re.search(r'(%s)\s+(credit )?cards?'%p,l): nets.append(n)
    allm=re.search(r'(all|any)\s+(%s)[\w\s/-]{0,30}(credit )?cards?'%brand,l)
    if hit and len(hit)<=max(1,int(0.6*len(pool))):
        ev=None
        return {'scope':'card','rule':'card_names_matched_on_official_page','issuer_ids':[iss],'card_ids':hit,'networks':[],'confidence':'stated','evidence_text':ev},hit
    if nets and not allm and len(nets)<3:
        ids=[c['id'] for c in pool if set(c['networks'])&set(nets)]
        return {'scope':'issuer_network','rule':'issuer_cards_on_named_network(s)','issuer_ids':[iss],'networks':nets,'card_ids':[],'confidence':'stated','evidence_text':None},ids
    ids=[c['id'] for c in pool]
    return {'scope':'issuer','rule':'all_issuer_credit_cards' if allm else 'issuer_wide_no_card_restriction_found','issuer_ids':[iss],'networks':[],'card_ids':[],'confidence':'stated' if allm else 'inferred','evidence_text':allm.group(0) if allm else None},ids
offers=[];skipped={'expired':0,'non_card':0,'http':0,'thin':0,'dupe':0};seen=set()
for iss,urls in cands.items():
    cc=iss_cfg[iss]['country']
    for u in urls:
        m,b=fetch(u)
        if m['status']!=200 or not b: skipped['http']+=1; continue
        text=visible_text(b)
        t=(meta(b,'og:title') or h1(b) or ptitle(b) or '').strip()
        t=re.split(r'\s+[|]\s+',t)[0].strip()
        t=re.sub(r'\s+[-–]\s+(AEON Credit Servic\w*|Standard Chartered \w+|Hong Leong Bank|HLB|CIMB \w+|UOB \w+|DBS \w+|Citibank \w+|Public Bank|AmBank|Alliance Bank|al ?rajhi bank \w*|HSBC \w+)\s*$','',t,flags=re.I).strip()
        if len(t)<6 or len(text)<300: skipped['thin']+=1; continue
        hh=h1(b) or t
        i0=text.find(hh[:25]) if hh else -1
        if i0<0: i0=text.find(t[:25])
        main=text[i0:i0+5000] if i0>=0 else text[:5000]
        ok,why=is_card_offer(t,main)
        if not ok: skipped['non_card']+=1; continue
        desc=meta(b,'og:description') or meta(b,'description')
        v=validity(main) or validity(text)
        key=(iss,t.lower())
        if key in seen: skipped['dupe']+=1; continue
        seen.add(key)
        el,ids=eligibility(iss,main,t)
        merch=merchant_from_title(t)
        lk=links(u)
        o={'id':f"{cc.lower()}-{slug(iss.split('-',1)[1]+'-'+t)}",'country':cc,'currency':CCY[cc],'title':t,'description':desc,
           'issuer_id':iss,'network':None,'merchant_ids':[],'_merchant_name':merch,
           'category':category(t),'benefit':benefit(t),'min_spend_text':min_spend(text),'validity':v,
           'eligibility':el,'eligible_card_ids':ids,'cross_border':{'merchant_country':None,'card_issuing_countries':[cc]},
           'terms_url':terms_url(lk),'source_url':m['final_url'] if m['final_url'].startswith('http') else u,'source_verified':True,
           'sources':[{'url':u,'kind':'issuer_promotion_page','fetched_at':m.get('fetched_at')}]}
        if o['category']=='other' and desc: o['category']=category(desc)
        if o['benefit']['type']=='other' and o['category']=='other' and not merch: skipped['unclassified']=skipped.get('unclassified',0)+1; continue
        offers.append(o)
from collections import Counter
for iss in {o['issuer_id'] for o in offers}:
    O=[o for o in offers if o['issuer_id']==iss]
    vc=Counter(o['validity']['valid_until'] for o in O if o['validity'])
    for o in O:
        if o['validity'] and len(O)>=5 and vc[o['validity']['valid_until']]>0.4*len(O): o['validity']=None
for iss in {o['issuer_id'] for o in offers}:
    O=[o for o in offers if o['issuer_id']==iss and o['eligibility']['scope']=='card']
    n=len([o for o in offers if o['issuer_id']==iss])
    cnt=Counter(cid for o in O for cid in o['eligibility']['card_ids'])
    noisy={cid for cid,k in cnt.items() if n>=5 and k>0.4*n}
    pool=[c['id'] for c in cards if c['issuer_id']==iss]
    for o in O:
        keep=[cid for cid in o['eligibility']['card_ids'] if cid not in noisy]
        if keep: o['eligibility']['card_ids']=keep; o['eligible_card_ids']=keep
        else:
            o['eligibility']={'scope':'issuer','rule':'issuer_wide_no_card_restriction_found','issuer_ids':[iss],'networks':[],'card_ids':[],'confidence':'inferred','evidence_text':None}
            o['eligible_card_ids']=pool
# Maybank MY listing (WebFetch transcription)
L=open('raw/manual/my-maybank.offers.txt').read().split('\n'); src=L[0].split(' ',1)[1]
mb=[c for c in cards if c['issuer_id']=='my-maybank']
for l in L[2:]:
    if not l.strip(): continue
    t,elig=[x.strip() for x in l.split('|')]
    nets=networks_in(elig) if elig else []
    if nets and 'and maybank islamic' not in elig.lower():
        el={'scope':'issuer_network','rule':'issuer_cards_on_named_network(s)','issuer_ids':['my-maybank'],'networks':nets,'card_ids':[],'confidence':'stated','evidence_text':elig}
        ids=[c['id'] for c in mb if set(c['networks'])&set(nets)]
    else:
        el={'scope':'issuer','rule':'all_issuer_credit_cards' if elig else 'issuer_wide_no_card_restriction_found','issuer_ids':['my-maybank'],'networks':[],'card_ids':[],'confidence':'stated' if elig else 'assumed','evidence_text':elig or None}
        ids=[c['id'] for c in mb]
    offers.append({'id':'my-'+slug('maybank-'+t),'country':'MY','currency':'MYR','title':t,'description':None,'issuer_id':'my-maybank','network':None,'merchant_ids':[],
     '_merchant_name':merchant_from_title(t),'category':category(t),'benefit':benefit(t),'min_spend_text':None,'validity':None,'eligibility':el,'eligible_card_ids':ids,
     'cross_border':{'merchant_country':None,'card_issuing_countries':['MY']},'terms_url':None,'source_url':src,'source_verified':True,
     'sources':[{'url':src,'kind':'issuer_promotion_listing','fetched_at':None}]})
json.dump(offers,open('raw/offers_built.json','w'),indent=1,ensure_ascii=False)
print(len(offers),skipped)
