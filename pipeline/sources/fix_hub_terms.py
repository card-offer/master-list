"""Replace hub-page terms on listing-hub offers with each deal's own T&C (source sweep, 10 Nov 2026).
 - my-rhb: each tile on the RHB promotions hub opens a popup that links the deal's own T&C PDF.
   terms = that PDF; dates = PDF period, else the popup's own text, else the tile's 'Valid until'.
 - sg-ocbc: deals have no page or T&C document of their own (text sits in a popup on the hub, served
   from the public listing JSON). terms_url therefore null; dates only from the deal's own popup text;
   the listing JSON display window is not used as an end date.
Reads raw/hubfix/*.orig.json (first-run backups of raw/extra_offers files); idempotent.
Run after the adapters and before merge_extra.py. Log: raw/hubfix/report.json"""
import sys,os,re,json,shutil,html as H
sys.path[:0]=['scripts','scripts/sources']
from fetch import fetch; from hfetch import doc; from extract import visible_text
import terms as TM
D='raw/hubfix'; os.makedirs(D,exist_ok=True)
def orig(name):
    src=f'raw/extra_offers/{name}.json'; bk=f'{D}/{name}.orig.json'
    if not os.path.exists(bk): shutil.copy(src,bk)
    return json.load(open(bk)),src
def norm(s): return re.sub(r'[^a-z0-9]','',(s or '').lower())
LOG=[]
DT=r'\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\.?\s+20\d\d'
VA=re.compile(r'\bValid\b[^.]{0,80}?\b(?:from|between)\s+(now|[^.]{1,40}?)\s+(?:to|till|until|and|\u2013|-)\s+('+DT+')',re.I)
VB=re.compile(r'\bValid\b[^.]{0,60}?\b(?:till|until|up to|through|thru)\s+('+DT+')',re.I)
def ocbc_period(text):
    """OCBC popups state the deal window in a leading 'Valid from X to Y' / 'Valid till Y' sentence."""
    t=TM.flat(text); hits=[]
    for m in VA.finditer(t):
        e=TM._single(m.group(2)); 
        if not e: continue
        if m.group(1).lower()=='now': a=None
        else:
            r=TM._range(t[m.start(1):m.end(2)]); a=r[1].isoformat() if r and r[2]==e[0][2] else None
        hits.append((m.start(),{'valid_from':a,'valid_until':e[0][2].isoformat(),'text':m.group(0)[:300]})); break
    m=VB.search(t)
    if m:
        e=TM._single(m.group(1))
        if e: hits.append((m.start(),{'valid_from':None,'valid_until':e[0][2].isoformat(),'text':m.group(0)[:300]}))
    return sorted(hits,key=lambda h:h[0])[0][1] if hits else None
def setdates(o,cands,pf=None):
    """cands: [(text,url,label)] in order of authority. First stated period wins."""
    old=(o.get('start_date'),o.get('end_date'))
    for txt,url,lab in cands:
        p=(pf or TM.period)(txt) if txt else None
        if p:
            o['start_date']=p['valid_from']; o['end_date']=p['valid_until']; o['dates_source_url']=url
            o['start_date_reason']=None if p['valid_from'] else f'{lab} states only an end date'
            o['end_date_status']='stated'; o['validity']={'valid_from':p['valid_from'],'valid_until':p['valid_until'],'text':p['text']}
            return lab,old
    o['start_date']=o['end_date']=None; o['validity']=None; o['dates_source_url']=None
    o['end_date_status']='evergreen'; o['start_date_reason']='no promotion period in the deal T&C or its own text'
    return None,old
def spend_cap(o,cands):
    o['min_spend']=o['cap']=None; o['min_spend_text']=None
    for txt,url,lab in cands:
        if not txt: continue
        if not o['min_spend']:
            ms=TM.min_spend(txt)
            if ms: o['min_spend']={'text':ms,'source_url':url}; o['min_spend_text']=ms
        if not o['cap']:
            c=TM.cap(txt)
            if c: o['cap']={'text':c,'source_url':url}
# ---------------- RHB
RHUB='https://www.rhbgroup.com/cards/promotions-privileges/index.html'
d,src=orig('my-rhb__rhb')
m,b=fetch(RHUB)
st=list(re.finditer(r'<div class="card-root[^>]*activePopUp = \'(\{[^}]+\})\'',b)); cards={}
for j,s in enumerate(st):
    seg=b[s.start(): st[j+1].start() if j+1<len(st) else s.start()+200000]; pid=s.group(1)
    h3=re.search(r'<h3[^>]*>(.*?)</h3>',seg,re.S); p=re.search(r'<p class="text-gray-2">(.*?)</p>',seg,re.S)
    vu=re.search(r'Campaign period</h4>\s*<h4[^>]*>(.*?)</h4>',seg,re.S)
    pi=seg.find("activePopUp != '"+pid+"'"); pop=seg[pi:] if pi>0 else ''
    pdfs=[]
    for x in re.findall(r'href\s*=\s*["\']([^"\']+\.pdf)["\']',pop,re.I):
        x=re.sub(r'^-/','/-/',x); x='https://www.rhbgroup.com'+x if x.startswith('/') else x
        x=x.replace(' ','%20')
        if x not in pdfs and not re.search(r'(?i)contact|general_tnc',x): pdfs.append(x)
    name=visible_text(h3.group(1)).strip() if h3 else ''; head=visible_text(p.group(1)).strip() if p else ''
    poptxt=visible_text(pop.split('">',1)[-1]) if pop else ''
    cards[norm(f"{name.title()}: {head}")]={'pid':pid,'name':name,'head':head,'valid':visible_text(vu.group(1)).strip() if vu else '','pdfs':pdfs,'pop':poptxt}
n=0
for o in d['offers']:
    if o.get('terms_url')!=RHUB: continue
    n+=1; c=cards.get(norm(o['title']))
    if not c:  # multi-promotion tiles: the adapter title starts with the tile's first promotion line
        mn=norm(o.get('_merchant_name') or o['title'].split(': ')[0]); ds=norm(o.get('description'))
        hit=[x for x in cards.values() if mn and any(norm(l).startswith(mn[:40]) for l in [x['head']]+x['head'].split('\n')) and norm(x['name']) in ds]
        if len(hit)==1:
            c=hit[0]; o['_merchant_name']=c['name'].title()
            o['title']=f"{c['name'].title()}: "+' / '.join(l.strip() for l in c['head'].split('\n') if l.strip())
            o['title_fixed_from_tile']=True
    rec={'issuer':'my-rhb','id':o['id'],'title':o['title'],'old_end':o.get('end_date'),'old_start':o.get('start_date')}
    if not c: rec['result']='tile_not_found_on_hub'; o['terms']=None; o['terms_url']=None; setdates(o,[]); LOG.append(rec); continue
    pdf=None; ptxt=''
    for u in c['pdfs']:
        dm,t=doc(u)
        if dm.get('status')==200 and dm.get('kind')=='pdf' and len(t.strip())>80: pdf=(u,dm,t); break
        rec.setdefault('pdf_errors',[]).append(f"{u} {dm.get('status')} {dm.get('kind')} {len(t.strip())}")
    cands=[]
    if pdf:
        u,dm,t=pdf; ptxt=t
        o['terms']={'url':u,'fetched_at':dm['fetched_at'],'kind':'pdf','hash':TM.sha(t),'clauses':TM.clauses(t)[:200]}
        o['terms_url']=u; o['terms_hash']=o['terms']['hash']; o['terms_fetched_at']=dm['fetched_at']
        cands.append((t,u,'deal T&C PDF')); rec['terms']=u
    else:
        o['terms']=None; o['terms_url']=None; o['terms_hash']=None; o['terms_fetched_at']=None
        rec['terms']=None; rec['terms_null_reason']='no deal-specific T&C link in the deal popup' if not c['pdfs'] else 'deal T&C link not readable'
    cands+= [(c['pop'],RHUB,'deal popup text'),(c['valid'],RHUB,'deal tile')]
    lab,old=setdates(o,cands); rec.update(dates_from=lab,new_end=o['end_date'],new_start=o['start_date'],dates_text=(o.get('validity') or {}).get('text'))
    # cross-check: what the popup/tile itself says
    pp=TM.period(c['pop']) or TM.period(c['valid'])
    rec['popup_end']=pp['valid_until'] if pp else None
    spend_cap(o,cands)
    o['sources']=[s for s in o['sources'] if s.get('url')!=RHUB or s.get('kind')=='issuer_promotion_page']
    LOG.append(rec)
json.dump(d,open(src+'.tmp','w'),indent=1,ensure_ascii=False); os.replace(src+'.tmp',src)
print('rhb hub offers',n)
# ---------------- OCBC SG
OHUB='https://www.ocbc.com/personal-banking/cards/card-promotion'; JU='https://www.ocbc.com/iwov-resources/sg/ocbc/personal/data/promotions-v1.json'
d,src=orig('sg-ocbc__ocbcsg')
m,b=fetch(JU); R={r.get('id'):r for r in json.loads(b).get('visiblePromo',[])}
def txt(x): return visible_text('<div>'+H.unescape(x or '')+'</div>') if x else ''
n=0
for o in d['offers']:
    if o.get('terms_url')!=OHUB: continue
    n+=1; r=R.get(o.get('ocbc_id')); rec={'issuer':'sg-ocbc','id':o['id'],'title':o['title'],'ocbc_id':o.get('ocbc_id'),'old_end':o.get('end_date'),'old_start':o.get('start_date'),'old_dates_source':o.get('dates_source_url')}
    o['terms']=None; o['terms_url']=None; o['terms_hash']=None; o['terms_fetched_at']=None
    rec['terms']=None; rec['terms_null_reason']='deal has no page or T&C document of its own; its T&C is a popup on the hub page'
    if not r: rec['result']='record_not_in_listing_json'; setdates(o,[]); LOG.append(rec); continue
    tt=txt((r.get('popup') or {}).get('terms')); ft=txt((r.get('popup') or {}).get('FreeText'))
    cands=[(tt,OHUB,'deal popup T&C'),(ft,OHUB,'deal popup text')]
    lab,old=setdates(o,cands,ocbc_period)
    if not lab: lab,old=setdates(o,cands); lab=lab and lab+' (generic period parser)'
    dt=r.get('date') or {}
    rec.update(dates_from=lab,new_end=o['end_date'],new_start=o['start_date'],dates_text=(o.get('validity') or {}).get('text'),listing_json_end=(dt.get('end') or '')[:10])
    spend_cap(o,cands)
    o['sources']=[s for s in o['sources'] if not (s.get('url')==OHUB and s.get('kind')!='issuer_promotion_page')]
    LOG.append(rec)
json.dump(d,open(src+'.tmp','w'),indent=1,ensure_ascii=False); os.replace(src+'.tmp',src)
print('ocbc hub offers',n)
json.dump(LOG,open(f'{D}/report.json','w'),indent=1,ensure_ascii=False)
from collections import Counter
for iss in ('my-rhb','sg-ocbc'):
    L=[x for x in LOG if x['issuer']==iss]
    print(iss,len(L),'terms set',sum(1 for x in L if x.get('terms')),'null',sum(1 for x in L if not x.get('terms')),
          'end changed',sum(1 for x in L if x['old_end']!=x.get('new_end') and x.get('new_end')),'end now missing',sum(1 for x in L if not x.get('new_end')),Counter(x.get('dates_from') for x in L))
