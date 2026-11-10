"""Build one offer record from an official page (+ its own T&C when linked). Never invents values:
anything not found in the source text stays null. Used by the per-issuer adapters in scripts/sources/adapters.py."""
import sys,re,json,os,html as H,urllib.parse,unicodedata,datetime; sys.path.insert(0,'pipeline')
from fetch import fetch; from hfetch import render,doc; from extract import visible_text,networks_in
import terms as TM; from offer_extract import category,benefit as benefit_title,merchant_from_title
CCY={'MY':'MYR','SG':'SGD'}
cards=json.load(open('raw/cards_built.json'))
if os.path.exists('raw/extra_cards/cards.json'): cards+=json.load(open('raw/extra_cards/cards.json'))['cards']
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
def slug(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().replace('&',' and ').replace('+',' plus ')
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')[:80]
def noem(s): return s.replace('\u2014',' - ').replace('\u2013','-') if isinstance(s,str) else s
ORGDOC=re.compile(r'charter|privacy|whistle|pidm|insured|auction|annual-report|tariff|fees-and-charges|interest-rate|product-disclosure|pds|brochure|notice|card[\s_%20-]*design',re.I)
GENERIC=re.compile(r'website-terms|general-terms|terms-of-use|privacy|cookie|cardmember-agreement|card-?member-agreement|customer-terms|standard-terms|universal-terms|/terms-and-conditions/?$|/terms-conditions/?$|/tnc/?$|/terms/?$|pdpa|disclaimer|e-?banking|security',re.I)
def tc_links(b,base):
    out=[]
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',b,flags=re.S|re.I):
        h=urllib.parse.urljoin(base,H.unescape(m.group(1).strip())); t=' '.join(H.unescape(re.sub('<[^>]+>',' ',m.group(2))).split())
        if h.startswith('http') and re.search(r'terms|tnc|t&c|\bt-c\b|conditions|syarat|\.pdf',urllib.parse.unquote(h)+' '+t,re.I) and re.search(r'terms|t\s?&\s?c|tnc|\bt-c\b|conditions|syarat|download',urllib.parse.unquote(h)+' '+t,re.I) and not GENERIC.search(h.split('?')[0]) and not ORGDOC.search(h) and not re.search(r'privacy|general|governing|website|cookie',t,re.I):
            out.append((h,t))
    return out
CUR=r'(?:RM|S\$|SGD|MYR|\$)\s?([\d,]+(?:\.\d+)?)'
def num(s): return float(s.replace(',','')) if s else None
def benefit_num(title,text=''):
    b=benefit_title(title)
    l=title
    m=re.search(r'(\d+(?:\.\d+)?)\s?%\s*(off|discount|savings?|cash\s?back|rebate)',l,re.I)
    if m: b.update(value=float(m.group(1)),unit='percent')
    else:
        m=re.search(CUR+r'\s*(?:(?:bonus|instant|extra|cash|e-?wallet)\s+){0,2}(off|discount|rebate|cash\s?back|savings?|voucher|e-?voucher|instant rebate|credit)',l,re.I)
        if m: b.update(value=num(m.group(1)),unit='currency')
        else:
            m=re.search(r'(\d+)\s?x\s*(points|treats|bonus|ocbc\$|uni\$|miles)',l,re.I)
            if m: b.update(value=float(m.group(1)),unit='multiplier')
    if 'value' not in b: b.update(value=None,unit=None)
    if re.search(r'up to',l[:m.start()] if m else '',re.I): b['up_to']=True
    if not b.get('value_text'): b['value_text']=None
    b.pop('value_pct',None)
    return b
def bnf(title,main):
    b=benefit_num(title)
    if b['type']=='other' and main:
        for sent in re.split(r'(?<=[.!\n])\s+',main[:1200]):
            if re.search(r'\d\s?%|RM\s?\d|S\$\s?\d|1[- ]for[- ]1|complimentary|cashback|rebate|0%',sent,re.I):
                b2=benefit_num(sent.strip()[:200])
                if b2['type']!='other': b2['value_text']=b2.get('value_text') or sent.strip()[:160]; b2['source']='offer_text'; return b2
    return b
def min_spend(text):
    s=TM.min_spend(text)
    if not s: return None
    m=re.search(CUR,s); return {'amount':num(m.group(1)) if m else None,'text':s}
def cap(text):
    s=TM.cap(text)
    if not s: return None
    m=re.search(CUR,s); return {'amount':num(m.group(1)) if m else None,'text':s}
def norm(s): return re.sub(r'[^a-z0-9+ ]+',' ',s.lower().replace('®','').replace('™','')).split()
def eligibility(iss,text,brand):
    pool=[c for c in cards if c['issuer_id']==iss]
    t=' '+' '.join(norm(text))+' '; hit=[]
    for c in pool:
        n=' '.join(w for w in norm(c['name']) if w not in ('credit','card','cards','the','i'))
        if len(n)>6 and (' '+n+' ') in t: hit.append(c['id'])
    l=text.lower()
    allm=re.search(r'(all|any)\s+(eligible\s+)?(%s)[\w\s/-]{0,30}(credit )?cards?'%brand,l) if brand else None
    if hit and len(hit)<=max(1,int(0.6*len(pool))):
        return {'scope':'card','rule':'card_names_matched_on_official_page','issuer_ids':[iss],'card_ids':hit,'networks':[],'confidence':'stated','evidence_text':None},hit
    nets=[]
    for n in networks_in(text[:4000]) if text else []:
        if re.search(r'(%s)[\w\s/-]{0,25}%s'%(brand or 'x^',n.lower()),l) or re.search(r'%s\s+(credit )?cards?'%n.lower(),l): nets.append(n)
    if nets and not allm and len(nets)<3:
        ids=[c['id'] for c in pool if set(c.get('networks') or [])&set(nets)]
        return {'scope':'issuer_network','rule':'issuer_cards_on_named_network(s)','issuer_ids':[iss],'networks':nets,'card_ids':[],'confidence':'stated','evidence_text':None},ids
    ids=[c['id'] for c in pool]
    return {'scope':'issuer','rule':'all_issuer_credit_cards' if allm else 'issuer_wide_no_card_restriction_found','issuer_ids':[iss],'networks':[],'card_ids':[],'confidence':'stated' if allm else 'inferred','evidence_text':allm.group(0) if allm else None},ids
STOPW=set('the and with for your you on at of to in a an by up off get enjoy card cards credit bank promotion promotions offer offers deals deal campaign html page en my sg personal pdf tnc terms conditions www com'.split())
def toks(x): return {w for w in re.findall(r'[a-z0-9]+',urllib.parse.unquote(x).lower()) if len(w)>2 and w not in STOPW and not w.isdigit()}
def best_tc(L,title,page_url):
    if not L: return None
    tt=toks(title)|toks(urllib.parse.urlparse(page_url).path)
    def sc(h,t):
        s=2*len(tt&toks(urllib.parse.urlparse(h).path))
        if re.search(r'tnc|terms|t-c|syarat',h,re.I): s+=1
        if h.lower().split('?')[0].endswith('.pdf'): s+=1
        return s
    r=sorted(L,key=lambda x:-sc(*x))
    return r[0][0] if sc(*r[0])>=2 else None
KW=re.compile(r'period|tempoh|terms|valid|spend|RM\s?\d|S\$\s?\d|\d%|until|cardholder|cardmember',re.I)
def main_block(vt,title):
    """Pick the occurrence of the title that is followed by the most offer-like text."""
    t=title[:30].strip()
    if not t: return vt[:8000]
    best=(-1,0)
    for m in re.finditer(re.escape(t),vt):
        sc=len(KW.findall(vt[m.start():m.start()+2500]))
        if sc>best[0]: best=(sc,m.start())
    out=vt[best[1]:best[1]+8000] if best[0]>=0 else vt[:8000]
    cut=RELATED.search(out,200)
    return out[:cut.start()] if cut else out
RELATED=re.compile(r'(?im)^\s*(other promotions|related promotions|you may also like|you may also be interested|more promotions|other deals|similar offers|latest promotions)\b')
def page(u,headless=False):
    m,b=fetch(u); mode='static'
    if headless or m['status']!=200 or len(visible_text(b).split())<300:
        hm,hb=render(u)
        if hb and (m['status']!=200 or len(visible_text(hb))>len(visible_text(b))): m,b,mode=hm,hb,'headless'
    return m,b,mode
def build(iss,cc,title,source_url,snippet=None,detail_url=None,tnc_url=None,merchant=None,brand='',kind='issuer_promotion_page',headless=False,listing_url=None):
    """snippet: the offer's own block of text on a listing page. detail_url: the offer's own page."""
    title=noem(' '.join(title.split()))
    srcs=[]; main=snippet or ''; page_url=detail_url or source_url
    if detail_url:
        m,b,mode=page(detail_url,headless)
        if m['status']==200 and b:
            vt=visible_text(re.sub(r'(?is)<(header|footer|nav)\b.*?</\1>',' ',b))
            from extract import h1 as _h1
            main=(main+'\n'+main_block(vt,(_h1(b) or title))).strip()
            srcs.append({'url':detail_url,'kind':kind,'fetched_at':m.get('fetched_at')})
            if not tnc_url:
                tnc_url=best_tc(tc_links(b,m['final_url']),title,detail_url)
        else: return None,f'detail page status {m["status"]}'
    if listing_url: srcs.append({'url':listing_url,'kind':'issuer_promotion_listing','fetched_at':None})
    if not srcs: srcs.append({'url':source_url,'kind':kind,'fetched_at':None})
    terms=None; ttext=None
    if tnc_url:
        dm,dt=doc(tnc_url)
        if dm['status']==200 and dt:
            ttext=dt if dm.get('kind')=='pdf' else visible_text(dt)
            if len(ttext)>200:
                terms={'url':dm['final_url'] if dm['final_url'].startswith('http') else tnc_url,'fetched_at':dm['fetched_at'],'kind':dm.get('kind'),'hash':TM.sha(ttext),'clauses':TM.clauses(ttext)[:200]}
            else: ttext=None
    if not terms and snippet:  # the deal's own T&C bullets on the listing page
        terms={'url':page_url,'fetched_at':now(),'kind':'page_section','hash':TM.sha(snippet),'clauses':TM.clauses(snippet)}
    elif not terms and detail_url and len(main)>200:  # no separate T&C document: the offer page's own text is its terms
        terms={'url':page_url,'fetched_at':now(),'kind':'page_section','hash':TM.sha(main),'clauses':TM.clauses(main)[:200],'note':'no separate T&C document linked; clauses from the offer page itself'}
    per=TM.period(ttext) if ttext else None; dsrc=terms['url'] if (per and terms) else None
    if not per:
        per=TM.period(main) or (TM.period(snippet) if snippet else None); dsrc=page_url if per else None
    start=per['valid_from'] if per else None; end=per['valid_until'] if per else None
    body=(ttext or '')+'\n'+main
    el,ids=eligibility(iss,title+'\n'+(snippet or main[:5000]),brand)
    merch=merchant or merchant_from_title(title)
    o={'id':f"{cc.lower()}-{slug(iss.split('-',1)[1]+'-'+title)}",'country':cc,'currency':CCY[cc],'title':title,
       'description':noem(re.sub(r'\s+',' ',snippet)[:400]) if snippet else None,'issuer_id':iss,'network':None,'merchant_ids':[],'_merchant_name':merch,
       'category':category(title+' '+(merch or '')),'benefit':bnf(title,snippet or main),
       'min_spend':min_spend(body),'cap':cap(body),'min_spend_text':(min_spend(body) or {}).get('text'),
       'validity':({'valid_from':start,'valid_until':end,'text':noem(per['text'])} if per else None),
       'start_date':start,'start_date_reason':None if start else ('source states only an end date' if end else 'no promotion period found in source'),
       'end_date':end,'end_date_status':'stated' if end else 'evergreen',
       'eligibility':el,'eligible_card_ids':ids,'cross_border':{'merchant_country':None,'card_issuing_countries':[cc]},
       'terms_url':terms['url'] if terms else tnc_url,'terms':terms,'terms_hash':terms['hash'] if terms else None,'terms_fetched_at':terms['fetched_at'] if terms else None,
       'source_url':page_url,'source_verified':True,'sources':srcs,'adapter':'pipeline/sources/adapters.py','dates_source_url':dsrc}
    if o['category']=='other' and snippet: o['category']=category(snippet[:300])
    return o,None
CUR_ADAPTER=None
# hub pages and non-credit-card products that slipped past the card check
NOT_CARD_OFFER={'my-cimb':r'^(Latest Promotions|CIMB CashLite|Prime Enhanced Campaign|CIMB Clicks FPX Campaign|CIMB Sole Prop Program|Wasiat Launch Campaign)$',
 'sg-maybank':r'^Cards Promotions$','sg-gxs':r'^(GXS Bank|GXS Debit Card)$','sg-hsbc':r'^HSBC General Terms','sg-posb':r'^Lifestyle Privileges$','sg-dbs':r'^(Lifestyle Privileges|DBS Cards Offers?)$'}
def save(iss,offers,meta=None):
    os.makedirs('raw/extra_offers',exist_ok=True)
    name=f'{iss}__{CUR_ADAPTER}' if CUR_ADAPTER else iss
    seen=set(); out=[]; dropped=[]
    for o in offers:
        x=NOT_CARD_OFFER.get(iss)
        if x and re.search(x,o['title']): dropped.append(o['title']); continue
        if o['id'] in seen: o['id']+='-'+str(len(seen))
        seen.add(o['id']); out.append(o)
    tmp=f'raw/extra_offers/{name}.json.tmp'
    meta=dict(meta or {}); meta['dropped_not_card_offer']=dropped
    json.dump({'issuer_id':iss,'generated_at':now(),'meta':meta,'offers':out},open(tmp,'w'),indent=1,ensure_ascii=False)
    os.replace(tmp,f'raw/extra_offers/{name}.json')

def apply_header_end(o,txt,url):
    """Listing card states 'Valid until <date>': that is the stated end date. Start kept only when the
    offer's own text states a 'from' date ending on the same day; otherwise null with reason."""
    ss=TM._single(txt)
    if not ss: return
    end=ss[0][2].isoformat()
    v=o.get('validity') or {}
    start=v.get('valid_from') if (v.get('valid_until')==end and re.search(r'from',v.get('text') or '',re.I)) else None
    o['end_date']=end; o['end_date_status']='stated'; o['start_date']=start
    o['start_date_reason']=None if start else 'listing states only an end date (Valid until)'
    o['validity']={'valid_from':start,'valid_until':end,'text':'Valid until '+txt.strip()}
    o['dates_source_url']=url
