import sys,re,json,unicodedata; sys.path.insert(0,'pipeline'); from fetch import fetch,meta as fmeta; from extract import *
cfg={c['id']:c for c in json.load(open('pipeline/issuers_config.json'))}
cands=json.load(open('raw/card_candidates.json'))
allc=[u for v in cands.values() for u in v]
CCY={'MY':'MYR','SG':'SGD'}
def slug(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().replace('&',' and ').replace('+',' plus ')
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')
def resolve(u):
    if fmeta(u) or u.startswith('LISTING:'): return u
    m=[c for c in allc if c.startswith(u.rstrip('/')[:len(u)-8])]
    return m[0] if len(m)==1 else u
def tokens_ok(name,text):
    t=text.lower().replace('\u2019',"'")
    toks=[w for w in re.findall(r"[a-z0-9+']+",name.lower().replace('\u2019',"'")) if len(w)>2 and w not in ('the','card','credit','and','for','bank','visa','mastercard','american','express')]
    miss=[w for w in toks if w not in t]
    return not miss, miss
def card_type(name,flags):
    if 'charge' in flags: return 'charge'
    return 'credit'
rows=[l.rstrip('\n').split('\t') for l in open('pipeline/cards_curated.tsv') if l.strip() and not l.startswith('#')]
cards=[];problems=[]
def mk(iss,name,url,text,b,nets_override,flags,listing=False,listing_line=None,fetched_at=None):
    cc=cfg[iss]['country']
    nets=[n for n in nets_override.split(',') if n] if nets_override else networks_in(name)
    net_src='name' if not nets_override and nets else ('curated_from_page' if nets_override else None)
    if not nets and text:
        hm=' '.join(filter(None,[title(b) if b else '',h1(b) if b else '',meta(b,'description') if b else '']))
        nets=networks_in(hm); net_src='page_heading' if nets else None
        if not nets:
            cnt={n:len(re.findall(p,text.lower())) for n,p in NET}
            hit=[n for n,c in cnt.items() if c>=2]
            if len(hit)==1: nets=hit; net_src='page_text'
            elif not hit:
                hit=[n for n,c in cnt.items() if c>=1]
                if len(hit)==1: nets=hit; net_src='page_text'
    isl=('islamic' in flags) or islamic(name)
    src_text=listing_line if listing_line is not None else text
    ok,miss=tokens_ok(name,text) if text else (False,['no_text'])
    c={'id':f"{cc.lower()}-{slug(name)}",'name':name,'issuer_id':iss,'country':cc,'currency':CCY[cc],
       'network':nets[0] if len(nets)==1 else None,'networks':nets,'network_source':net_src,
       'tier':tier_of(name),'card_type':card_type(name,flags),'islamic':isl,
       'status':'no_new_applications' if 'no_new_applications' in flags else 'active',
       'annual_fee':None,'min_income':None,'benefits':[],
       'official_url':url,'sources':[{'url':url,'kind':'issuer_listing' if listing else 'issuer_product_page','fetched_at':fetched_at}],
       'name_verified_on_source':ok,'benefits_scope':'card'}
    if src_text:
        mi=min_income(src_text); af=annual_fee(src_text)
        if mi: c['min_income']={**mi,'source_url':url}
        if af: c['annual_fee']={**af,'source_url':url}
        for bnf in benefits(src_text)[:40]:
            bnf['source_url']=url; c['benefits'].append(bnf)
    if not ok: problems.append((c['id'],'name tokens missing',miss))
    return c
for r in rows:
    r+=['']*(5-len(r)); iss,url,name,nets,flags=r[:5]; flags=flags.split(',') if flags else []
    listing=url.startswith('LISTING:'); url=url.replace('LISTING:','')
    url=resolve(url); m,b=fetch(url)
    if m['status']!=200: problems.append((name,'http',m['status'],url)); 
    text=visible_text(b) if b else ''
    line=None
    if listing:
        # only the block for this card on the listing page
        i=text.lower().find(name.lower().replace('fifa world cup 2026','fifa world cup 2026™').split(' credit card')[0].lower())
        line=text[i:i+400] if i>=0 else ''
    cards.append(mk(iss,name,url,text,b,nets,flags,listing,line,m.get('fetched_at') if isinstance(m, dict) else None))
    if sum(1 for rr in rows if rr[1].replace('LISTING:','')==r[1].replace('LISTING:',''))>1 and not listing: cards[-1]['benefits_scope']='shared_product_page'
# manual listings (WebFetch transcriptions)
for f,iss in [('raw/manual/my-maybank.listing.txt','my-maybank'),('raw/manual/sg-maybank.listing.txt','sg-maybank')]:
    L=open(f).read().split('\n'); src=L[0].split(' ',1)[1]
    full='\n'.join(L)
    for l in L[2:]:
        if not l.strip(): continue
        name,inc,ben=[x.strip() for x in l.split('|')]
        if name.startswith('American Express') or name.startswith('Singapore Airlines'): disp=name
        else: disp=name
        c=mk(iss,disp,src,full,None,'',[],True,(inc+'\n'+ben.replace('; ','\n')))
        cards.append(c)
# drop issuer-wide boilerplate sentences (nav teasers, footers) seen on many distinct product pages
from collections import defaultdict
pages=defaultdict(lambda: defaultdict(set))
for c in cards:
    for bn in c['benefits']: pages[c['issuer_id']][bn['text']].add(c['official_url'])
npages={i:len({c['official_url'] for c in cards if c['issuer_id']==i}) for i in pages}
for c in cards:
    i=c['issuer_id']; n=npages[i]
    if n>=3:
        c['benefits']=[bn for bn in c['benefits'] if len(pages[i][bn['text']])<max(3,0.4*n)]
# de-dup ids
seen={}
for c in cards:
    if c['id'] in seen: seen[c['id']]+=1; c['id']+=f"-{seen[c['id']]}"
    else: seen[c['id']]=1
json.dump(cards,open('raw/cards_built.json','w'),indent=1,ensure_ascii=False)
print(len(cards)); [print(p) for p in problems]
