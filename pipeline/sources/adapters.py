import html
"""Per-issuer listing adapters. Each returns offer records built by offerlib.build from official pages only.
Usage: python3 scripts/sources/adapters.py <adapter> [...]"""
import sys,re,json,urllib.parse; sys.path.insert(0,'pipeline'); sys.path.insert(0,'pipeline/sources')
import offerlib as OL, ws
import terms as TM
from fetch import fetch; from hfetch import render,close; from extract import visible_text
from links import links
LOG=open('raw/sources/adapters.log','a')
def log(*a): print(*a,flush=True); print(*a,file=LOG,flush=True)
def end_ceiling():
    from lib.rules import load_rules
    return load_rules()["listing_end_date_ceiling"]
DEBIT_ONLY=re.compile(r'debit card',re.I)
def is_credit(text): return bool(re.search(r'credit card|kad kredit|credit/debit|credit or debit|credit cards?/-?i|cardmember|cardholders?',text,re.I))
def lines(text): return [l.strip() for l in text.split('\n') if l.strip()]
def run_blocks(iss,cc,url,blocks,brand,listing_kind='issuer_promotion_listing'):
    out=[];skip={}
    for blk in blocks:
        title,merchant,snip,detail=blk[:4]; hdr_end=blk[4] if len(blk)>4 else None
        if not is_credit(title+' '+snip) and not detail: skip['not_credit']=skip.get('not_credit',0)+1; continue
        o,why=OL.build(iss,cc,title,url,snippet=snip,detail_url=detail,merchant=merchant,brand=brand,listing_url=url if detail else None)
        if o and hdr_end: OL.apply_header_end(o,hdr_end,url)
        # expired offers are kept; publish assigns status and the archive path
        if o: out.append(o)
        else: skip[why.split(' ')[0]]=skip.get(why.split(' ')[0],0)+1
    return out,skip
# ---------------- RHB MY ----------------
def rhb():
    iss='my-rhb'; allo=[]; meta={}
    u='https://www.rhbgroup.com/cards/promotions-privileges/index.html'
    m,b=fetch(u); L=lines(visible_text(b)); blocks=[]
    idx=[i for i in range(len(L)-2) if L[i+2]=='Campaign period']
    for j,i in enumerate(idx):
        end=idx[j+1] if j+1<len(idx) else min(len(L),i+60)
        name=L[i]; head=L[i+1]; body=L[i+3:end]
        # body repeats name/head, then bullets
        if len(body)>2 and body[1]==name: body=body[3:]
        snip='\n'.join(body)
        if not is_credit(snip+head): continue
        hd=re.search(r'Valid until (.+)',L[i+3]) if i+3<len(L) else None
        blocks.append((f"{name.title()}: {head}",name.title(),snip,None,hd.group(1) if hd else None))
    o,s=run_blocks(iss,'MY',u,blocks,'rhb'); allo+=o; meta[u]={'offers':len(o),'skipped':s,'blocks':len(blocks)}
    ws.upd(u,status='done',offers_found=str(len(o)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"static listing; {len(blocks)} credit-card blocks; skipped {s}")
    log('rhb promos',len(blocks),len(o),s)
    # Mastercard specials: each 'Learn more' -> detail page
    u2='https://www.rhbgroup.com/cards/mastercard-offers/index.html'
    m2,b2=fetch(u2); L2=lines(visible_text(b2))
    pdfs=[]
    for x in re.findall(r'href\s*=\s*["\']([^"\']+\.pdf)["\']',b2,flags=re.I):
        x=urllib.parse.urljoin(u2,x)
        if x not in pdfs: pdfs.append(x)
    heads=[(L2[i-2],L2[i-1]) for i in range(2,len(L2)) if L2[i]=='Learn more']
    log('rhb mc blocks',len(heads),'pdfs',len(pdfs))
    o2=[]; s2={}
    def cmp(x): return re.sub(r'[^a-z]','',x.lower())
    def pick(name):
        n=cmp(name)
        for pdf in sorted(pdfs,key=lambda q:-len(q)):
            stem=cmp(re.sub(r'^tnc-(mc-)?','',pdf.rsplit('/',1)[-1][:-4]))
            if stem and (stem in n or n in stem or (len(stem)>=4 and n.startswith(stem[:4]) and stem[:6] in n)): return pdf
        return None
    for name,head in heads:
        pdf=pick(name)
        if not pdf: s2['no_tnc_pdf_matched']=s2.get('no_tnc_pdf_matched',0)+1; continue
        o,why=OL.build(iss,'MY',f"{name}: {head}",u2,snippet=head,tnc_url=pdf,merchant=name,brand='rhb mastercard|rhb')
        if o:
            o['eligibility']={'scope':'issuer_network','rule':'issuer_cards_on_named_network(s)','issuer_ids':[iss],'networks':['mastercard'],'card_ids':[],'confidence':'stated','evidence_text':'Spend with your RHB Mastercard Credit Cards/-i'}
            o['eligible_card_ids']=[c['id'] for c in OL.cards if c['issuer_id']==iss and 'mastercard' in (c.get('networks') or [])]
            o2.append(o)
        else: s2[why.split(' ')[0]]=s2.get(why.split(' ')[0],0)+1
    det=pdfs
    allo+=o2; meta[u2]={'offers':len(o2),'skipped':s2,'detail_links':len(det)}
    ws.upd(u2,status='done',offers_found=str(len(o2)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"{len(det)} detail pages; skipped {s2}")
    log('rhb mc',len(o2),s2)
    for u3 in ['https://www.rhbgroup.com/ApplyandSpendCard/index.html','https://www.rhbgroup.com/btcx/index.html']:
        mm,bb=fetch(u3); ttl=re.search(r'<title>(.*?)</title>',bb,re.S); ttl=re.sub(r'^RHB\s*\|\s*','',ttl.group(1).strip()) if ttl else u3
        h1=re.search(r'<h1[^>]*>(.*?)</h1>',bb,re.S); h1=re.sub('<[^>]+>','',h1.group(1)).strip() if h1 else ttl
        o,why=OL.build(iss,'MY',h1 or ttl,u3,detail_url=u3,brand='rhb')
        if o: allo.append(o)
        ws.upd(u3,status='done',offers_found='1' if o else '0',date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=why or '')
    OL.save(iss,allo,meta); return allo
A={"rhb":rhb}
# ---------------- generic: listing page(s) -> offer detail pages ----------------
from extract import h1 as _h1, meta as _meta, title as _ptitle
import extract as _EX
_BADH=re.compile(r"(?i)^(i'?m looking for|i am looking for|search|menu|reach us|filter|share|exclusive food deals .*promotions in singapore)$|^(i'?m looking for)")
def _h1(b):
    for mm in re.finditer(r'(?is)<h[12][^>]*>(.*?)</h[12]>',b):
        t=' '.join(html.unescape(re.sub('<[^>]+>',' ',mm.group(1))).split())
        if t and not _BADH.search(t): return t
    return None
_EX.h1=_h1
from offer_extract import is_card_offer
def detail_links(listing,pat,headless=False):
    out=[]; ms=[]
    for mode in (['static','headless'] if headless else ['static']):
        m,b=(render(listing) if mode=='headless' else fetch(listing)); ms.append(m)
        if not b: continue
        base=m.get('final_url') or listing
        for mm in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',b,flags=re.S|re.I):
            h=urllib.parse.urljoin(base,mm.group(1).strip().replace('&amp;','&'))
            if re.search(pat,h) and h not in out and h.split('?')[0].rstrip('/')!=listing.split('?')[0].rstrip('/'): out.append(h)
    m=next((x for x in ms if x.get('status')==200),ms[0])
    return out,m
def clean_title(t):
    t=re.split(r'\s+[|]\s+',t or '')[0].strip()
    return re.sub(r'\s+[-\u2013\u2014|]\s+[A-Z][\w ]{2,40}(Bank|Berhad|Malaysia|Singapore|Bhd)\.?\s*$','',t).strip()
HSBCSG_HUBS={'dining','travel-leisure','lifestyle-shopping','daily-spend','favourites','general-tnc-sg','exclusive-spend'}
def generic(iss,cc,listings,pat,brand,headless=False,cap=150,detail_headless=False,require_card=True):
    allo=[]; meta={}; seen=set()
    for lu in listings:
        try: det,m=detail_links(lu,pat,headless)
        except Exception as e: det=[]; m={'status':0,'error':str(e)}
        o_here=0; s={}
        for h in det[:cap]:
            if h in seen: continue
            seen.add(h)
            if h.lower().split('?')[0].endswith('.pdf'):
                from hfetch import doc
                dm,dt=doc(h)
                if dm['status']!=200 or len(dt)<200: s['pdf_http']=s.get('pdf_http',0)+1; continue
                nm=urllib.parse.unquote(h.rsplit('/',1)[-1][:-4])
                nm=re.sub(r'[-_]+',' ',re.sub(r'(?i)[-_ ]*(promotion|promo|details?|summary|sumamry|final|tnc|t&c|terms|20\d\d|v\d)\b','',nm)).strip()
                first=' '.join(dt.split())[:1200]
                o,why=OL.build(iss,cc,f"{nm}: card promotion",lu,snippet=first,tnc_url=h,merchant=nm,brand=brand,listing_url=lu)
                if o: o['source_url']=h; o['detail_level']='pdf_only'; allo.append(o); o_here+=1
                else: k=why.split(' ')[0]; s[k]=s.get(k,0)+1
                continue
            if OL.CUR_ADAPTER=='hsbcsg' and h.rstrip('/').rsplit('/',1)[-1] in HSBCSG_HUBS: s['category_hub']=s.get('category_hub',0)+1; continue
            mm,bb,mode=OL.page(h,detail_headless)
            if mm['status']!=200 or not bb: s['http']=s.get('http',0)+1; continue
            t=clean_title(_meta(bb,'og:title') or _h1(bb) or _ptitle(bb) or '')
            if OL.CUR_ADAPTER=='hsbcsg' and t and len(t)<45:
                hs=[' '.join(html.unescape(re.sub('<[^>]+>',' ',x)).split()) for x in re.findall(r'(?is)<h[1-3][^>]*>(.*?)</h[1-3]>',bb)]
                if t in hs:
                    nx=hs[hs.index(t)+1] if hs.index(t)+1<len(hs) else ''
                    if re.search(r'(?i)\d\s?%|S\$\s?\d|\boff\b|cashback|complimentary|1-for-1|rebate|miles',nx): t=f"{t}: {nx}"
            vt=visible_text(bb)
            if len(t)<5: s['no_title']=s.get('no_title',0)+1; continue
            if require_card:
                i=vt.find(t[:20]); main=vt[i:i+5000] if i>=0 else vt[:5000]
                ok,why=is_card_offer(t,main)
                if not ok: s[why]=s.get(why,0)+1; continue
            o,why=OL.build(iss,cc,t,lu,detail_url=h,brand=brand,listing_url=lu,headless=detail_headless)
            if o: allo.append(o); o_here+=1
            else: k=why.split(' ')[0]; s[k]=s.get(k,0)+1
        meta[lu]={'detail_links':len(det),'offers':o_here,'skipped':s,'listing_status':m.get('status')}
        st='done' if det else 'blocked'
        note=f"{len(det)} detail pages; {o_here} offers; skipped {s}" if det else f"no offer links found (status {m.get('status')}{', JS-rendered' if not headless else ''})"
        ws.upd(lu,status=st,offers_found=str(o_here),date_checked=ws.now(),last_verified=ws.now()[:10] if det else '',notes_blockers=note)
        log(iss,lu,meta[lu])
    OL.save(iss,allo,meta); return allo
def muamalat():
    return generic('my-muamalat','MY',['https://www.muamalat.com.my/promotions/card/'],r'muamalat\.com\.my/promotion/[a-z0-9-]+/?$','muamalat|bank muamalat')
A['muamalat']=muamalat

def reg(name,iss,cc,listings,pat,brand,**kw): A[name]=lambda: generic(iss,cc,listings,pat,brand,**kw)
reg('bankislam','my-bank-islam','MY',['https://www.bankislam.com/promotions/'],r'bankislam\.com/(promotions/[a-z0-9-]+/?$|wp-content/uploads/.*(Promo|Promotion).*\.pdf$)','bank islam')
reg('affin','my-affin','MY',['https://www.affinalways.com/en/promotions?group=Personal&product_filter=Cards'],r'affinalways\.com/promotions/.+\?v=','affin',headless=True,detail_headless=True)
reg('bsn','my-bsn','MY',['https://www.bsn.com.my/IslamicBanking/Cards-i/credit-card-promotions','https://www.bsn.com.my/page/highlights-promotions'],r'bsn\.com\.my/(page/[A-Za-z0-9-]+|cms/upload/pdf/promotion/.+\.pdf)','bsn',headless=True)
reg('ocbcmy','my-ocbc','MY',['https://www.ocbc.com.my/personal-banking/promotion'],r'ocbc\.com\.my/personal-banking/(campaign|promotion)/[a-z0-9-]+','ocbc',headless=True)
reg('hsbcsg','sg-hsbc','SG',['https://www.hsbc.com.sg/card-promotions','https://cardpromotions.hsbc.com.sg/'],r'(cardpromotions\.hsbc\.com\.sg|hsbc\.com\.sg/card-promotions)/[a-z0-9-]+','hsbc',headless=True,detail_headless=True,require_card=False)
reg('posb','sg-posb','SG',['https://www.posb.com.sg/personal/cards/offers/default.page','https://www.posb.com.sg/personal/cards/promotions/default.page']+['https://www.posb.com.sg/personal/cards/offers/1-for-1', 'https://www.posb.com.sg/personal/cards/offers/buy-now-pay-later', 'https://www.posb.com.sg/personal/cards/offers/daily-essentials', 'https://www.posb.com.sg/personal/cards/offers/default.page', 'https://www.posb.com.sg/personal/cards/offers/dine', 'https://www.posb.com.sg/personal/cards/offers/overseas-deals', 'https://www.posb.com.sg/personal/cards/offers/shop', 'https://www.posb.com.sg/personal/cards/offers/travel'],r'posb\.com\.sg/personal/(promotion|deals|cards/offers)/[a-z0-9-]+','posb',headless=True,require_card=False)
reg('maybanksg','sg-maybank','SG',['https://cardspromo.maybank2u.com.sg/','https://cardspromo.maybank2u.com.sg/promotions?category=Dining','https://cardspromo.maybank2u.com.sg/promotions?category=Travel','https://cardspromo.maybank2u.com.sg/promotions?category=Lifestyle','https://cardspromo.maybank2u.com.sg/promotions?category=Essentials','https://cardspromo.maybank2u.com.sg/promotions?category=Pets','https://cardspromo.maybank2u.com.sg/promotions?category=Malaysia+Deals','https://cardspromo.maybank2u.com.sg/promotions?category=Worldwide+Deals'],r'cardspromo\.maybank2u\.com\.sg/promotions/[a-z0-9-]+$','maybank',require_card=False)
reg('boc','sg-boc','SG',['https://www.bankofchina.com/sg/bcservice/bc3/'],r'bankofchina\.com/sg/bcservice/bc3/\d+/t\d+_\d+\.html','boc|bank of china')
reg('ocbcsg','sg-ocbc','SG',['https://www.ocbc.com/personal-banking/cards/card-promotion'],r'ocbc\.com/personal-banking/(cards/card-promotions/|campaign/)[a-z0-9-]+','ocbc',headless=True,detail_headless=True)
reg('dbsoffers','sg-dbs','SG',['https://www.dbs.com.sg/personal/cards/offers/default.page'],r'dbs\.com\.sg/personal/(promotion|deals)/[a-z0-9-]+','dbs',headless=True)
def ocbcsg_json():
    """OCBC SG card promotions page loads its listing from a public static JSON file; each record carries
    the deal's own popup text and T&C HTML. Dates: T&C text first, the listing's own start/end second."""
    import html as H, datetime
    iss='sg-ocbc'; page='https://www.ocbc.com/personal-banking/cards/card-promotion'
    ju='https://www.ocbc.com/iwov-resources/sg/ocbc/personal/data/promotions-v1.json'
    m,b=fetch(ju); d=json.loads(b); allo=[]; s={}
    def txt(x): return visible_text('<div>'+H.unescape(x or '')+'</div>') if x else ''
    for r in d.get('visiblePromo',[]):
        title=f"{r.get('title','').strip()}: {r.get('link','').strip()}".strip(': ')
        free=txt((r.get('popup') or {}).get('FreeText')); terms=txt((r.get('popup') or {}).get('terms'))
        snip=(free+'\n'+terms).strip()
        if not snip: s['no_text']=s.get('no_text',0)+1; continue
        o,why=OL.build(iss,'SG',title,page,snippet=snip,merchant=r.get('title','').strip() or None,brand='ocbc')
        if not o: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1; continue
        dt=r.get('date') or {}
        def pd(x):
            try: return datetime.datetime.strptime(x.split(' ')[0],'%d/%m/%Y').date().isoformat()
            except Exception: return None
        js,je=pd(dt.get('start','')),pd(dt.get('end',''))
        if not o['end_date'] and je and je<=end_ceiling():
            o['end_date']=je; o['end_date_status']='stated_listing_data'; o['start_date']=js; o['start_date_reason']=None if js else 'listing data has no start'
            o['validity']={'valid_from':js,'valid_until':je,'text':'listing data date window '+(dt.get('start') or '')+' to '+(dt.get('end') or '')}; o['dates_source_url']=ju
        # expired offers are kept; publish assigns status and the archive path
        o['terms']=dict(o['terms'] or {},url=page,kind='listing_json_terms_html',data_url=ju)
        o['terms_url']=page; o['sources'].append({'url':ju,'kind':'issuer_listing_data_json','fetched_at':m['fetched_at'][:10]})
        o['category_hint']=r.get('main_cat'); o['ocbc_id']=r.get('id')
        allo.append(o)
    OL.save(iss,allo,{'json':ju,'skipped':s,'visible':len(d.get('visiblePromo',[]))})
    ws.upd(page,status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"JS page; listing read from its public data file {ju}; {len(d.get('visiblePromo',[]))} visible records; skipped {s}")
    log('ocbcsg',len(allo),s); return allo
A['ocbcsg']=ocbcsg_json
reg('dbsoffers','sg-dbs','SG',['https://www.dbs.com.sg/personal/cards/offers/default.page','https://www.dbs.com.sg/personal/cards/promotions/default.page']+['https://www.dbs.com.sg/personal/cards/offers/1-for-1', 'https://www.dbs.com.sg/personal/cards/offers/dine', 'https://www.dbs.com.sg/personal/cards/offers/shop', 'https://www.dbs.com.sg/personal/cards/offers/travel', 'https://www.dbs.com.sg/personal/cards/offers/daily-essentials', 'https://www.dbs.com.sg/personal/cards/offers/overseas-deals', 'https://www.dbs.com.sg/personal/cards/offers/buy-now-pay-later'],r'dbs\.com\.sg/personal/(promotion|deals|cards/offers)/[a-z0-9-]+','dbs',headless=True,require_card=False)
def json_list_detail(iss,cc,page,ju,key,brand,pathk='path',titlek='brand',require_card=True,headless=False):
    m,b=fetch(ju); d=json.loads(b); items=d.get(key,[]); allo=[]; s={}
    for it in items:
        h=urllib.parse.urljoin(page,it.get(pathk) or '')
        if not h.startswith('http'): continue
        mm,bb,mode=OL.page(h,headless)
        if mm['status']!=200: s['http']=s.get('http',0)+1; continue
        t=clean_title(it.get(titlek) or _meta(bb,'og:title') or _h1(bb) or '')
        if require_card:
            vt=visible_text(bb); ok,why=is_card_offer(t,vt[:8000])
            if not ok: s[why]=s.get(why,0)+1; continue
        o,why=OL.build(iss,cc,t,page,detail_url=h,brand=brand,listing_url=page,snippet=None)
        if o and not o['end_date'] and it.get('validityPeriod'): OL.apply_header_end(o,it['validityPeriod'],page)
        # expired offers are kept; publish assigns status and the archive path
        if o: o['sources'].append({'url':ju,'kind':'issuer_listing_data_json','fetched_at':None}); allo.append(o)
        else: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1
    OL.save(iss,allo,{'json':ju,'items':len(items),'skipped':s})
    ws.upd(page,status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"listing data {ju}: {len(items)} items; skipped {s}")
    log(iss,len(items),len(allo),s); return allo
A['cimbmy']=lambda: json_list_detail('my-cimb','MY','https://www.cimb.com.my/en/personal/promotions/latest-promotions.html','https://www.cimb.com.my/en/personal/promotions/latest-promotions/_jcr_content/root/responsivegrid_197111812/promo_listing_copy_c.list','listing','cimb')
def pairs(iss,cc,brand,items,listing,merge=True):
    """items: (title_or_None, detail_url_or_None, tnc_url_or_None). Titles are copied from the official page."""
    allo=[]; s={}
    for t,d,tc in items:
        if not t and d:
            mm,bb,mode=OL.page(d,True); t=clean_title(_meta(bb,'og:title') or _h1(bb) or _ptitle(bb) or '')
        o,why=OL.build(iss,cc,t,listing,detail_url=d,tnc_url=tc,brand=brand,listing_url=listing if d else None,headless=True)
        if o: allo.append(o)
        else: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1
    OL.save(iss,allo,{'listing':listing,'skipped':s})
    ws.upd(listing,status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"{len(items)} offer entries read; skipped {s}")
    log(iss,len(items),len(allo),s); return allo
A['gxs']=lambda: pairs('sg-gxs','SG','gxs',[
 ('JB weekend perks with GXS FlexiCard','https://www.gxs.com.sg/flexicard-jb-weekend','https://www.gxs.com.sg/flexicard-jb-weekend-terms'),
 ('20% rebate on Singtel & GOMO bills with GXS FlexiCard',None,'https://www.gxs.com.sg/flexicard-singtelgomo-rebate-terms'),
 ('Get a S$15 Shell voucher with GXS FlexiCard',None,'https://www.gxs.com.sg/shell-terms')],'https://www.gxs.com.sg/flexicard')
A['maribank']=lambda: pairs('sg-maribank','SG','mari',[
 ('Spend Overseas with Mari Credit Card Promotion',None,'https://banking-aka-storage.maribank.com.sg/maribank/sg/website-content/Spend_Overseas_with_Mari_Credit_Card_Promotion_Terms_&_Conditions_06102026.pdf'),
 ('FX Rates with Mari Credit Card Promotion',None,'https://banking-aka-storage.maribank.com.sg/maribank/sg/website-content/FX_Rates_with_Mari_Credit_Card_Promotion_Terms_&_Conditions_07092026.pdf'),
 ('Earn 1.5% Shopee Coins on Shopee Spend with Mari Credit Card (2027) Promotion',None,'https://banking-aka-storage.maribank.com.sg/maribank/sg/website-content/Earn_1.5%_Shopee_Coins_on_Shopee_Spend_with_Mari_Credit_Card_(2027)_Promotion_Terms_&_Conditions_07092026.pdf')],'https://www.maribank.sg/product/mari-credit-card')
A['dcs']=lambda: pairs('sg-dcs','SG','dcs|diners club',[
 (None,'https://dcscc.com/dinersclub75',None),(None,'https://dcscc.com/GoEcoTogether',None),(None,'https://dcscc.com/personal/axs',None),
 (None,'https://cards.dcscc.com/ultimate',None),(None,'https://cards.dcscc.com/cashback',None),(None,'https://cards.dcscc.com/dconvertoffer',None)],'https://dcscc.com/campaigns')
reg('dcsdeals','sg-dcs','SG',['https://dcscc.com/merchant-deals','https://dcscc.com/promotions'],r'dcscc\.com/(merchant-deals|promotions|deals)/[A-Za-z0-9-]+','dcs|diners club',headless=True,detail_headless=True,require_card=False)
reg('gxspromos','sg-gxs','SG',['https://www.gxs.com.sg/promotions'],r'gxs\.com\.sg/[a-z0-9-]*(flexicard|card)[a-z0-9-]*$','gxs',headless=True,require_card=False)
reg('hsbcmy','my-hsbc','MY',['https://sp.hsbc.com.my/','https://sp.hsbc.com.my/category/all','https://sp.hsbc.com.my/category/food-and-beverages','https://sp.hsbc.com.my/category/health-and-beauty','https://sp.hsbc.com.my/category/shopping','https://sp.hsbc.com.my/category/0-card-instalment-plan'],r'sp\.hsbc\.com\.my/offers/\d+/[a-z0-9-]+','hsbc',headless=True,detail_headless=True,require_card=False,cap=200)
def bsn():
    lu='https://www.bsn.com.my/IslamicBanking/Cards-i/credit-card-promotions'
    m,b=render(lu,wait_ms=6000); L=lines(visible_text(b))
    i0=L.index('PROMOTIONS') if 'PROMOTIONS' in L else 0
    titles=[L[i-1] for i in range(i0,len(L)) if L[i]=='Discover']
    hrefs=[]
    for mm in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',b,flags=re.S|re.I):
        if re.sub('<[^>]+>','',mm.group(2)).strip()=='Discover':
            h=urllib.parse.urljoin(lu,mm.group(1)).split('?')[0]
            if h not in hrefs: hrefs.append(h)
    items=[(t,h,None) for t,h in zip(titles,hrefs) if not re.search(r'ewallet|debit',t,re.I)]
    log('bsn tiles',len(titles),len(hrefs),len(items))
    return pairs('my-bsn','MY','bsn',items,lu)
A['bsn']=bsn
def scsg_json(cc='SG'):
    """SC SG The Good Life page loads its offers from a public static JSON file; each record carries
    the offer text, its own T&C HTML and a start/end window. Dates: T&C text first, record window second."""
    import html as H, datetime
    lc=cc.lower(); iss=lc+'-standard-chartered'; page=f'https://www.sc.com/{lc}/promotions/the-good-life-privileges/'
    ju=f'https://www.sc.com/{lc}/data/tgl/offers.json'
    m,b=fetch(ju); recs=json.loads(b)['offers']['offer']; allo=[]; s={}
    def txt(x): return visible_text('<div>'+H.unescape(x or '')+'</div>') if x else ''
    def pd(x):
        try: return datetime.datetime.strptime((x or '').split(' ')[0],'%d-%m-%Y').date().isoformat()
        except Exception: return None
    for r in recs:
        name=' '.join((r.get('name') or '').split()); ot=' '.join(txt(r.get('otitle')).split()) or ' '.join((r.get('otitle') or '').split())
        title=f"{name}: {ot}".strip(': ')
        snip=(ot+'\n'+txt(r.get('odesc'))+'\n'+txt(r.get('tnc'))).strip()
        if not snip: s['no_text']=s.get('no_text',0)+1; continue
        su=page+'#offer-'+str(r.get('id'))
        o,why=OL.build(iss,cc,title,su,snippet=snip,merchant=name or None,brand='standard chartered|sc')
        if not o: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1; continue
        js,je=pd(r.get('sd')),pd(r.get('ed'))
        if not o['end_date'] and je and je<=end_ceiling():
            o['end_date']=je; o['end_date_status']='stated_listing_data'; o['start_date']=o['start_date'] or js; o['start_date_reason']=None if o['start_date'] else 'listing data has no start'
            o['validity']={'valid_from':o['start_date'],'valid_until':je,'text':'offer record window '+(r.get('sd') or '')+' to '+(r.get('ed') or '')}; o['dates_source_url']=ju
        # expired offers are kept; publish assigns status and the archive path
        if o['terms']: o['terms']=dict(o['terms'],url=su,kind='listing_json_terms_html',data_url=ju)
        o['terms_url']=su; o['sources'].append({'url':ju,'kind':'issuer_listing_data_json','fetched_at':m['fetched_at'][:10]})
        nets=[n for n,k in (('mastercard','mas'),('visa','visa')) if r.get(k)]
        if nets and (not o.get('eligibility') or o['eligibility'].get('scope')=='issuer'):
            pass
            o['eligibility']={'scope':'issuer_network','rule':'issuer_cards_on_named_network(s)','issuer_ids':[iss],'networks':nets,'card_ids':[],'confidence':'stated','evidence_text':'offer record network flags: '+', '.join(nets)}
            o['eligible_card_ids']=[c['id'] for c in OL.cards if c['issuer_id']==iss and set(c.get('networks') or [])&set(nets)]
        o['category_hint']=r.get('cat'); o['sc_id']=r.get('id')
        allo.append(o)
    OL.save(iss,allo,{'json':ju,'skipped':s,'records':len(recs)})
    ws.upd(page,country=cc,bank='Standard Chartered',page_type='merchant_offers',status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"JS page; offers read from its public data file {ju}; {len(recs)} records; skipped {s}")
    log(iss,len(recs),len(allo),s); return allo
A['scsg']=scsg_json
A['scmy']=lambda: scsg_json('MY')

def amexsg():
    """Amex SG Platinum campaign page: dated benefit blocks, each read from the page itself; welcome offer uses its PDF T&C."""
    iss='sg-amex'; page='https://www.americanexpress.com/en-sg/campaigns/the-platinum-card/'
    m,b=fetch(page); vt=visible_text(b); L=[l.strip() for l in vt.split('\n') if l.strip()]
    def block(start,stop_pat,n=12):
        i=next((k for k,l in enumerate(L) if l.startswith(start)),None)
        if i is None: return None
        out=[]
        for l in L[i:i+n]:
            if out and re.search(stop_pat,l): break
            out.append(l)
        return '\n'.join(out)
    specs=[('The Platinum Card: welcome Membership Rewards points offer','For New to American Express Card Members',r'^Offer Terms and Conditions','https://www.americanexpress.com/content/dam/amex/sg/campaigns/pdfs/the-platinum-card-welcomeoffer.pdf',20,None),
           ('The Platinum Card: S$200 Global Dining Credit','Global Dining Credit',r'^Love Dining',None,6,'Global Dining'),
           ('The Platinum Card: S$400 Platinum Wine Credit','Platinum Wine Credit',r'^Platinum Experiences',None,6,'Wine'),
           ('The Platinum Card: Regional Golf Programme complimentary green fees','Regional Golf Programme',r'^Discover full benefits',None,4,'Golf')]
    allo=[]; s={}
    for title,start,stop,tnc,n,merch in specs:
        sn=block(start,stop,n)
        if not sn: s['block_not_found']=s.get('block_not_found',0)+1; continue
        su=page+'#'+re.sub(r'[^a-z0-9]+','-',start.lower()).strip('-')
        o,why=OL.build(iss,'SG',title,su,snippet=sn,tnc_url=tnc,merchant=merch,brand='american express|amex')
        BV={'For New to American Express Card Members':('points_miles',200000.0,'points','Receive up to 200,000 Membership Rewards points',True),
            'Global Dining Credit':('other',200.0,'currency','enjoy S$200 in Global Dining Credits',False),
            'Platinum Wine Credit':('other',400.0,'currency','S$400 Platinum Wine Credit, presented as two S$200 credits',False),
            'Regional Golf Programme':('freebie',None,None,'complimentary green fees on us whenever you bring paying companion(s)',False)}
        if o and start in BV:
            t_,v_,u_,vt_,up_=BV[start]; assert re.sub(r'[\s,]','',vt_)[:18] in re.sub(r'[\s,®]','',sn), vt_
            o['benefit']={'type':t_,'value_text':vt_,'value':v_,'unit':u_,'source':'offer_text'}
            if up_: o['benefit']['up_to']=True
            if start.startswith('For New') and 'min. spending of S$15,000' in sn: o['min_spend']={'amount':15000.0,'text':'min. spending of S$15,000 within first 6 months of Card approval'}
        if o:
            pc=[c['id'] for c in OL.cards if c['issuer_id']==iss and c['name']=='The Platinum Card']
            if pc: o['eligibility']={'scope':'card','rule':'card_names_matched_on_official_page','issuer_ids':[iss],'card_ids':pc,'networks':[],'confidence':'stated','evidence_text':'The Platinum Card campaign page'}; o['eligible_card_ids']=pc
            o['sources']=[{'url':page,'kind':'issuer_promotion_page','fetched_at':m['fetched_at'][:10]}]+[x for x in o['sources'] if x['url']!=su]
            allo.append(o)
        else: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1
    OL.save(iss,allo,{'page':page,'skipped':s})
    ws.upd(page,status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"Platinum benefit blocks with a stated end date; skipped {s}; undated always-on benefits (Love Dining, Chillax, lounges) not recorded as offers")
    log(iss,len(allo),s); return allo
A['amexsg']=amexsg

def icbcsg():
    """ICBC SG English promotions column: titles from the listing link text (the detail pages carry only the site title)."""
    from render_rows import links_of
    lu='https://www.icbc.com.sg/en/column/1438058492253847697.html'
    m,b=render(lu); L=links_of(b,lu)
    items=[(re.sub(r'^\[Credit Card\]\s*','',t).strip(),h,None) for h,t in L.items() if re.search(r'icbc\.com\.sg/en/page/\d+\.html$',h) and t and not re.search(r'(?i)foreign exchange|remittance|advisory|notice|manual guide',t)]
    log('icbcsg items',len(items))
    return pairs('sg-icbc','SG','icbc',items,lu)
A['icbcsg']=icbcsg

def hsbcmy2():
    """HSBC MY Smart Privileges: offer pages carry merchant and offer headings plus an inline T&C section.
    Title = merchant heading + offer heading; terms = the page's own T&C section (the linked PDFs are site-wide)."""
    iss='my-hsbc'; cats=['https://sp.hsbc.com.my/','https://sp.hsbc.com.my/category/all','https://sp.hsbc.com.my/category/food-and-beverages','https://sp.hsbc.com.my/category/health-and-beauty','https://sp.hsbc.com.my/category/shopping','https://sp.hsbc.com.my/category/0-card-instalment-plan']
    pat=r'sp\.hsbc\.com\.my/offers/\d+/[a-z0-9-]+'; urls=[]
    for lu in cats:
        det,m=detail_links(lu,pat,True)
        for h in det:
            if h not in urls: urls.append(h)
    allo=[]; s={}
    for h in urls[:250]:
        mm,bb,mode=OL.page(h,True)
        if mm['status']!=200 or not bb: s['http']=s.get('http',0)+1; continue
        hs=[' '.join(html.unescape(re.sub('<[^>]+>',' ',x)).split()) for x in re.findall(r'(?is)<h[1-3][^>]*>(.*?)</h[1-3]>',bb)]
        hs=[x for x in hs if x and x not in ('Smart Privileges','Share Offer')]
        if len(hs)<2: s['no_heading']=s.get('no_heading',0)+1; continue
        merch=hs[0]; head=next((x for x in hs[1:] if x!=merch),None)
        if not head or head=='Terms and Conditions': s['no_offer_heading']=s.get('no_offer_heading',0)+1; continue
        vt=visible_text(bb); L=[l.strip() for l in vt.split('\n') if l.strip()]
        try: i=max(k for k,l in enumerate(L) if l==head)
        except ValueError: s['no_block']=s.get('no_block',0)+1; continue
        blk=[]
        for l in L[i:]:
            if l.startswith('You may also be interested'): break
            blk.append(l)
        sn='\n'.join(blk)
        o,why=OL.build(iss,'MY',f"{merch}: {head}",h,snippet=sn,merchant=merch,brand='hsbc|hsbc amanah',listing_url=cats[1])
        if not o: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1; continue
        o['sources']=[{'url':h,'kind':'issuer_promotion_page','fetched_at':mm.get('fetched_at')}]+[x for x in o['sources'] if x['url']!=h]
        if not o['end_date']:
            w=re.search(r'Offer starts from\s+(\d{2})/(\d{2})/(\d{4})\s+to\s+(\d{2})/(\d{2})/(\d{4})',vt)
            if w:
                a,b2=f"{w.group(3)}-{w.group(2)}-{w.group(1)}",f"{w.group(6)}-{w.group(5)}-{w.group(4)}"
                o.update(start_date=a,start_date_reason=None,end_date=b2,end_date_status='stated',dates_source_url=h,validity={'valid_from':a,'valid_until':b2,'text':w.group(0)})
        allo.append(o)
    OL.CUR_ADAPTER='hsbcmy'; OL.save(iss,allo,{'urls':len(urls),'skipped':s})
    for lu in cats: ws.upd(lu,status='done',date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"Smart Privileges offer pages read; site total {len(allo)} offers from {len(urls)} pages; skipped {s}")
    log(iss,'hsbcmy2',len(urls),len(allo),s); return allo
A['hsbcmy']=hsbcmy2

A['cimbsg']=lambda: pairs('sg-cimb','SG','cimb',[(None,'https://www.cimb.com.sg/en/personal/promotions/latest-promotions/cards/bts-contest.html',None),(None,'https://www.cimb.com.sg/en/personal/promotions/latest-promotions/cards/casa-x-vs.html',None)],'https://www.cimb.com.sg/en/personal/promotions/latest-promotions.html')

A['dcsextra']=lambda: pairs('sg-dcs','SG','dcs|diners club',[(None,'https://cards.dcscc.com/dconvertoffer',None),(None,'https://cards.dcscc.com/ultimate',None)],'https://cards.dcscc.com/dconvertoffer')
def uobsg():
    """UOB SG JB deals page: merchant tiles (slug_, category, name, headline, offer period) and, further down, each deal's T&C paragraph naming the merchant."""
    iss='sg-uob'; lu='https://www.uob.com.sg/personal/promotions/cards/jbdeals/index.page'
    m,b=fetch(lu); L=[l.strip() for l in visible_text(b).split('\n') if l.strip()]
    allo=[]; s={}
    for k,l in enumerate(L):
        if re.fullmatch(r'[a-z0-9_]+_',l) and k+4<len(L) and L[k+4].startswith('Offer period'):
            name,head,per=L[k+2],L[k+3],L[k+4]
            tc=next((x for x in L if len(x)>200 and name.lower() in x.lower() and re.search(r'(?i)offer is valid|the offer is valid',x)),None)
            sn='\n'.join([head,per]+([tc] if tc else []))
            su=lu+'#'+l.strip('_')
            o,why=OL.build(iss,'SG',f"{name}: {head.rstrip('.')}",su,snippet=sn,merchant=name,brand='uob')
            if o:
                o['cross_border']={'merchant_country':'MY','card_issuing_countries':['SG']}
                o['sources']=[{'url':lu,'kind':'issuer_promotion_page','fetched_at':m['fetched_at'][:10]}]
                allo.append(o)
            else: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1
    OL.save(iss,allo,{'listing':lu,'skipped':s})
    ws.upd(lu,status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"JB merchant deal tiles with inline T&C; skipped {s}; card-benefit blurbs and UNI$ redemption not recorded as offers")
    log(iss,'uobsg',len(allo),s); return allo
A['uobsg']=uobsg

reg('aeon','my-aeon-credit','MY',['https://myaeoncredit.com.my/promotions/'],r'myaeoncredit\.com\.my/promotions/[^/?#]+/?$','aeon')

reg('ambank','my-ambank','MY',['https://www.ambank.com.my/promotions'],r'ambank\.com\.my/(promotions/[^/?#]+|cards/credit-cards/[a-z-]*(offer|campaign|promo)[a-z-]*)$','ambank|amBank')

reg('hlb','my-hong-leong','MY',['https://www.hlb.com.my/en/personal-banking/promotions.html','https://www.hlb.com.my/en/personal-banking/promotions/cards-hlb-card-offers.html'],r'hlb\.com\.my/en/personal-banking/(promotions/(cards-|enrich|hlb-cards)[a-z0-9-]+\.html|credit-cards/[a-z0-9/-]*(offer|promo|deal)[a-z0-9-]*\.html)','hlb|hong leong',headless=True,detail_headless=True)

reg('alliance','my-alliance','MY',['https://www.alliancebank.com.my/promotions'],r'alliancebank\.com\.my/promotions/Cards/(?![^/]*debit-card)[A-Za-z0-9-]+$','alliance')

def hlbtiles():
    """HLB card offers page: inline tiles (date window, merchant, headline, notes, T&Cs link). T&C links paired by order of appearance."""
    import html as H
    iss='my-hong-leong'; lu='https://www.hlb.com.my/en/personal-banking/promotions/cards-hlb-card-offers.html'
    m,b=render(lu); L=[l.strip() for l in visible_text(b).split('\n') if l.strip()]
    tcs=[urllib.parse.urljoin(lu,H.unescape(x.group(1))) for x in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>\s*(?:<[^>]+>\s*)*T&amp;Cs\s*(?:<[^>]+>\s*)*</a>',b,re.I)]
    DL=re.compile(r'^\d{1,2}(\s+[A-Z][a-z]+)?(\s+\d{4})?\s*[-\u2013]\s*\d{1,2}\s+[A-Z][a-z]+\s+\d{4}$')
    allo=[]; s={}; ti=0; seen=set()
    idx=[k for k,l in enumerate(L) if l=='T&Cs']
    for n,k in enumerate(idx):
        j=k-1
        while j>0 and not DL.match(L[j]) and k-j<10: j-=1
        if not DL.match(L[j]): s['no_date']=s.get('no_date',0)+1; continue
        tile=[x for x in L[j+1:k] if x not in ('Book Now','Find out more')]
        if len(tile)<2: continue
        merch,head=tile[0],tile[1]
        tc=tcs[n] if n<len(tcs) and len(tcs)==len(idx) else None
        key=(merch,head)
        if key in seen: continue
        seen.add(key)
        sn='\n'.join(['Offer period: '+L[j].replace('\u2013','-')]+tile)
        o,why=OL.build(iss,'MY',f"{merch}: {head}",lu+'#'+re.sub(r'[^a-z0-9]+','-',(merch+' '+head).lower())[:60],snippet=sn,tnc_url=tc,merchant=merch,brand='hlb|hong leong')
        if o:
            per=TM.period(sn)
            if per and per.get('valid_until') and (not o['end_date'] or o['end_date']!=per['valid_until']) and not (o.get('terms') and o['terms'].get('kind')=='pdf' and o['end_date']):
                o.update(start_date=per['valid_from'],end_date=per['valid_until'],end_date_status='stated',dates_source_url=lu,validity=per)
            # expired offers are kept; publish assigns status and the archive path
            o['sources']=[{'url':lu,'kind':'issuer_promotion_page','fetched_at':m['fetched_at'][:10]}]+[x for x in o['sources'] if x['kind']!='issuer_promotion_page']
            allo.append(o)
        else: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1
    OL.save(iss,allo,{'listing':lu,'tiles':len(idx),'tnc_links':len(tcs),'skipped':s})
    ws.upd(lu,country='MY',bank='Hong Leong',page_type='merchant_offers',status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"{len(idx)} inline offer tiles, {len(tcs)} T&C links; skipped {s}")
    log(iss,'hlbtiles',len(idx),len(tcs),len(allo),s); return allo
A['hlbtiles']=hlbtiles

def pbb():
    """Public Bank: promo pages are mostly images; the deal's T&C is the /media/ PDF linked under 'Terms and Conditions'."""
    import html as H
    iss='my-public-bank'; lu='https://www.pbebank.com/en/promotions/credit-cards-promotions/'
    det,m=detail_links(lu,r'pbebank\.com/en/promotions/latest-promotions/(?!preferred-redemption|pb-cash-advance)[a-z0-9-]+/?$')
    allo=[]; s={}
    SITEWIDE=re.compile(r'(?i)wechat_pbb|faq-|pbepbeng|debit-card')
    for h in det:
        mm,bb,mode=OL.page(h)
        if mm['status']!=200: s['http']=s.get('http',0)+1; continue
        t=clean_title(_h1(bb) or _ptitle(bb) or '')
        vt=visible_text(bb); i=vt.rfind('Terms and Conditions')
        pdfs=[urllib.parse.urljoin(h,H.unescape(x)) for x in re.findall(r'href="([^"]+\.pdf[^"]*)"',bb) if not SITEWIDE.search(x)]
        tc=pdfs[0] if pdfs else None
        if not t: s['no_title']=s.get('no_title',0)+1; continue
        o,why=OL.build(iss,'MY',t,lu,detail_url=h,tnc_url=tc,brand='pb|public bank',listing_url=lu)
        if o: allo.append(o)
        else: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1
    OL.save(iss,allo,{'listing':lu,'detail_links':len(det),'skipped':s})
    ws.upd(lu,status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"{len(det)} promo pages (image-based); dates and terms from each deal's own T&C PDF; skipped {s}")
    log(iss,'pbb',len(det),len(allo),s); return allo
A['pbb']=pbb

def uobmy():
    """UOB MY deals category pages: inline tiles (slug, category, merchant, [tag], headline, 'Offer period:' date, T&C 'click here' link). Links paired by order only when counts match."""
    import html as H
    iss='my-uob'; base='https://www.uob.com.my/personal/promotions/'
    pages=[base+x for x in ['dining-deals.page','shopping-deals.page','travel-deals.page','lifestyle-deals.page','other-deals.page']]
    allo=[]; seen=set(); tot={}
    for lu in pages:
        m,b=fetch(lu)
        if m['status']!=200 or not b: ws.upd(lu,country='MY',bank='UOB',page_type='merchant_offers',status='blocked',date_checked=ws.now(),notes_blockers=f"HTTP {m['status']}"); continue
        L=[l.strip() for l in visible_text(b).split('\n') if l.strip()]
        hrefs=[urllib.parse.urljoin(lu,H.unescape(x.group(1))) for x in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>\s*click here\s*</a>',b,re.I)]
        idx=[k for k,l in enumerate(L) if l=='Offer period:']
        s={}; n_here=0
        for n,k in enumerate(idx):
            j=k-1
            while j>0 and not re.fullmatch(r'[a-z0-9_.&\'-]+',L[j]) and k-j<8: j-=1
            if not re.fullmatch(r'[a-z0-9_.&\'-]+',L[j]): s['no_slug']=s.get('no_slug',0)+1; continue
            tile=L[j+2:k]
            if len(tile)<2: s['short']=s.get('short',0)+1; continue
            rest=[t for t in tile[1:] if not re.match(r'(?i)promo ?code|shop now|store locator',t)] or tile[1:]
            merch,head=tile[0],rest[-1]; tag=rest[:-1]
            per=L[k+1] if k+1<len(L) else ''
            key=(merch,head)
            if key in seen: continue
            seen.add(key)
            tc=hrefs[n] if len(hrefs)==len(idx) else None
            if tc and not re.search(r'(?i)\.pdf|tnc|terms',tc): tc=None
            sn='\n'.join(tile+['Offer period: '+per])
            per2=TM.period('Offer period: '+per)
            if per.startswith('Now to'): per2=TM.period('valid until '+per[7:])
            o,why=OL.build(iss,'MY',f"{merch}: {head}",lu+'#'+L[j],snippet=sn,tnc_url=tc,merchant=merch,brand='uob')
            if not o: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1; continue
            if per2 and per2.get('valid_until') and not (o.get('terms') and o['terms'].get('kind')=='pdf' and o['end_date']):
                o.update(end_date=per2['valid_until'],end_date_status='stated',dates_source_url=lu,start_date=None if per.startswith('Now') else per2.get('valid_from'),start_date_reason='listing says Now to <date>' if per.startswith('Now') else None,validity={'valid_from':None if per.startswith('Now') else per2.get('valid_from'),'valid_until':per2['valid_until'],'text':'Offer period: '+per})
            # expired offers are kept; publish assigns status and the archive path
            if any(re.search(r'(?i)visa exclusive',t) for t in tag):
                o['eligibility']={'scope':'issuer_network','rule':'issuer_cards_on_named_network(s)','issuer_ids':[iss],'networks':['visa'],'card_ids':[],'confidence':'stated','evidence_text':'Visa Exclusive'}
                o['eligible_card_ids']=[c['id'] for c in OL.cards if c['issuer_id']==iss and 'visa' in (c.get('networks') or [])]
            if re.search(r'\b(TWD|THB|SGD|IDR|VND|JPY|KRW|HKD)\b|S\$',sn): o['cross_border']={'merchant_country':None,'card_issuing_countries':['MY']}
            o['sources']=[{'url':lu,'kind':'issuer_promotion_page','fetched_at':m['fetched_at'][:10]}]+[x for x in o['sources'] if x['kind']!='issuer_promotion_page']
            allo.append(o); n_here+=1
        tot[lu]=(len(idx),n_here,s)
        ws.upd(lu,country='MY',bank='UOB',page_type='merchant_offers',status='done',offers_found=str(n_here),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"{len(idx)} inline tiles, {len(hrefs)} T&C links; skipped {s}")
    OL.save(iss,allo,{'pages':tot})
    ws.upd(base+'index.page',status='done',date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers='hub; deals read from the category pages (uobmy adapter)')
    log(iss,'uobmy',len(allo),tot); return allo
A['uobmy']=uobmy

def ocbcmy2():
    """OCBC MY promotions page: each deal opens an inline panel (merchant, headline, 'Back to promotion list', details, T&C, 'Important Notes')."""
    iss='my-ocbc'; lu='https://www.ocbc.com.my/personal-banking/promotion'
    m,b=render(lu); L=[l.strip() for l in visible_text(b).split('\n') if l.strip()]
    allo=[]; s={}; seen=set()
    idx=[k for k,l in enumerate(L) if l=='Back to promotion list']
    for k in idx:
        merch,head=L[k-2],L[k-1]
        if (merch,head) in seen: continue
        seen.add((merch,head))
        e=next((j for j in range(k+1,min(len(L),k+80)) if L[j].startswith('Important Notes')),min(len(L),k+40))
        sn='\n'.join([head]+L[k+2:e])
        o,why=OL.build(iss,'MY',f"{merch}: {head}",lu+'#'+re.sub(r'[^a-z0-9]+','-',merch.lower()).strip('-'),snippet=sn,merchant=merch,brand='ocbc')
        if o:
            o['sources']=[{'url':lu,'kind':'issuer_promotion_page','fetched_at':m['fetched_at'][:10]}]
            allo.append(o)
        else: s[why.split(' ')[0]]=s.get(why.split(' ')[0],0)+1
    OL.CUR_ADAPTER='ocbcmy'; OL.save(iss,allo,{'listing':lu,'panels':len(idx),'skipped':s})
    ws.upd(lu,status='done',offers_found=str(len(allo)),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers=f"JS page rendered; {len(idx)} inline deal panels with their own T&C; skipped {s}")
    log(iss,'ocbcmy2',len(idx),len(allo),s); return allo
A['ocbcmy']=ocbcmy2

A['ocbcmycamp']=lambda: pairs('my-ocbc','MY','ocbc',[(None,'https://www.ocbc.com.my/personal-banking/campaign/mastercard-spend',None),(None,'https://www.ocbc.com.my/personal-banking/campaign/mickeygolocal',None)],'https://www.ocbc.com.my/personal-banking/campaign/mastercard-spend')

if __name__=='__main__':
    for a in sys.argv[1:]:
        OL.CUR_ADAPTER=a
        try: r=A[a](); log(a,'TOTAL',len(r), 'with end_date',sum(1 for o in r if o['end_date']))
        except Exception as e:
            import traceback; traceback.print_exc(); log(a,'ERROR',e)
    close()
