"""Cards for issuers added in the 10 Nov 2026 source sweep (not in the original 30). Same record shape as
raw/cards_built.json (build_cards.mk). Official pages only. Output: raw/extra_cards/cards.json"""
import sys,re,json,unicodedata; sys.path.insert(0,'pipeline'); sys.path.insert(0,'pipeline/sources')
from fetch import fetch; from hfetch import render,close; from extract import *
import ws
CCY={'MY':'MYR','SG':'SGD'}
def slug(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower().replace('&',' and ').replace('+',' plus ')
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')
def text_of(u,headless=False):
    m,b=fetch(u)
    if headless or m['status']!=200 or len(visible_text(b).split())<300:
        hm,hb=render(u)
        if hb and len(visible_text(hb))>len(visible_text(b)): m,b=hm,hb
    return m,b,visible_text(b) if b else ''
def block(text,name,n=900):
    i=text.find(name)
    return text[i:i+n] if i>=0 else ''
def mk(iss,cc,name,url,src_text,nets=None,listing=False):
    nets=nets or networks_in(name) or []
    ok=all(w.lower() in src_text.lower() for w in re.findall(r"[A-Za-z0-9+']{3,}",name) if w.lower() not in ('card','credit','the','and'))
    c={'id':f"{cc.lower()}-{slug(name)}",'name':name,'issuer_id':iss,'country':cc,'currency':CCY[cc],
       'network':nets[0] if len(nets)==1 else None,'networks':nets,'network_source':'name' if networks_in(name) else ('curated_from_page' if nets else None),
       'tier':tier_of(name),'card_type':'credit','islamic':islamic(name),'status':'active','annual_fee':None,'min_income':None,'benefits':[],
       'official_url':url,'sources':[{'url':url,'kind':'issuer_listing' if listing else 'issuer_product_page','fetched_at':None}],
       'name_verified_on_source':ok,'benefits_scope':'card','added_by':'pipeline/sources/cards_extra.py'}
    mi=min_income(src_text); af=annual_fee(src_text)
    if mi: c['min_income']={**mi,'source_url':url}
    if af: c['annual_fee']={**af,'source_url':url}
    for b in benefits(src_text)[:40]: b['source_url']=url; c['benefits'].append(b)
    return c
cards=[]; ISS=[]
# GXS (SG)
u='https://www.gxs.com.sg/flexicard'; m,b,t=text_of(u)
if m['status']==200: cards.append(mk('sg-gxs','SG','GXS FlexiCard',u,t)); ws.upd(u,status='done',cards_found='1',date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers='card network not stated on page')
ISS.append({'id':'sg-gxs','country':'SG','name':'GXS Bank','legal_name':'GXS Bank Pte. Ltd.','website':'https://www.gxs.com.sg','seeds':[u],'product':'/flexicard$'})
# MariBank (SG)
u='https://www.maribank.sg/product/mari-credit-card'; m,b,t=text_of(u)
if m['status']==200: cards.append(mk('sg-maribank','SG','Mari Credit Card',u,t)); ws.upd(u,status='done',cards_found='1',date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers='card network not stated on page')
ISS.append({'id':'sg-maribank','country':'SG','name':'MariBank','legal_name':'MariBank Singapore Private Limited','website':'https://www.maribank.sg','seeds':[u],'product':'/product/mari-credit-card$'})
# DCS Card Centre (SG): products listing (JS page, rendered)
u='https://cards.dcscc.com/products'; m,b,t=text_of(u,True)
names=[]
for l in t.split('\n'):
    l=l.strip()
    if re.match(r'^(DCS|COURTS)',l) and len(l)<70 and re.search(r'Card$|Mastercard$',l) and l not in names: names.append(l)
NETS={}  # network only when the card name states it; no inference
for n in names:
    if n=='DCS Flex Card': continue  # umbrella name; the issued product is 'DCS Flex Visa Platinum Card'
    nets=networks_in(n)
    if 'DeCard' in n: continue  # stablecoin-funded card; credit status unclear on page, left out
    cards.append(mk('sg-dcs','SG',n,u,block(t,n),nets=nets,listing=True))
ws.upd('https://cards.dcscc.com/',status='done',cards_found=str(sum(1 for c in cards if c['issuer_id']=='sg-dcs')),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers='card list read from rendered https://cards.dcscc.com/products (JS); DeCard stablecoin cards left out (credit status unclear)')
ISS.append({'id':'sg-dcs','country':'SG','name':'DCS Card Centre','legal_name':'DCS Card Centre Pte. Ltd.','website':'https://dcscc.com','seeds':[u],'product':'/products$'})
# ICBC Singapore
IC=[('ICBC Friendship Credit Card','https://www.icbc.com.sg/en/column/1143510810581213185.html'),('ICBC Horoscope Credit Card','https://www.icbc.com.sg/en/column/1438059017468788896.html'),
('ICBC Chinese Zodiac Credit Card','https://www.icbc.com.sg/en/column/1438059017535897814.html'),('ICBC Global Travel Mastercard Credit Card','https://www.icbc.com.sg/en/column/1438059017535897692.html'),
('CEA Friends Credit Card','https://www.icbc.com.sg/en/column/1438059017603006505.html'),('ICBC UnionPay Dual Currency Credit Card','https://www.icbc.com.sg/en/column/1438059017535897823.html'),
('ICBC VISA Dual Currency Credit Card','https://www.icbc.com.sg/en/column/1438059017468788827.html'),('ICBC Student Talent Credit Card','https://www.icbc.com.sg/en/column/1438059017468788837.html')]
n_ic=0
for n,u in IC:
    m,b,t=text_of(u)
    if m['status']!=200: continue
    # page body after the side menu: last occurrence of the card name
    i=t.rfind(n.replace(' Mastercard',' Mastercard®')) if 'Mastercard' in n else t.rfind(n)
    body=t[i:i+4000] if i>=0 else ''
    cards.append(mk('sg-icbc','SG',n,u,body or t)); n_ic+=1
ws.upd('https://www.icbc.com.sg/en/column/1438059017535897814.html',status='done',cards_found=str(n_ic),date_checked=ws.now(),last_verified=ws.now()[:10],notes_blockers='8 cards from the official Credit Cards menu; each card page fetched')
ISS.append({'id':'sg-icbc','country':'SG','name':'ICBC Singapore','legal_name':'Industrial and Commercial Bank of China Limited, Singapore Branch','website':'https://www.icbc.com.sg','seeds':['https://www.icbc.com.sg/en/column/1438059017535897814.html'],'product':'/en/column/\\d+\\.html$'})
json.dump({'issuers':ISS,'cards':cards},open('raw/extra_cards/cards.json','w'),indent=1,ensure_ascii=False)
for c in cards: print(c['issuer_id'],c['name'],c['networks'],bool(c['annual_fee']),bool(c['min_income']),len(c['benefits']),c['name_verified_on_source'])
close()
