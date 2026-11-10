"""Fill offer start/end dates, min spend, cap and own T&C clauses from each offer's T&C document or page.
Writes raw/terms_enriched.json keyed by offer source_url. Sequential: one host at a time, cached."""
import sys,re,json,html as H,urllib.parse,os; sys.path.insert(0,'pipeline')
from fetch import fetch; from hfetch import render,doc,close; from extract import visible_text,h1; import terms as TM
OUT='raw/terms_enriched.json'
GENERIC=re.compile(r'website-terms|general-terms|terms-of-use|terms-of-service|termsofuse|/terms/default|privacy|footer|electronic-services|governing|stc-governing|lost-card|faq|personal-loan|debit-card-renewal|cardmember-agreement|card-?member-agreement|client-terms|customer-terms|standard-terms|universal-terms|e-?banking|/terms-and-conditions/?$|/terms-conditions/?$|terms-conditions\.page$|/tnc/?$|/terms/?$|announcement|security|cookie|disclaimer|pdpa|personal-data|bonusaver|deposit|mortgage|home-loan|ttc|thankyou-rewards-tncs|sms-redemption|accounts-services|terms-of-access|products_tncs|/save/|/deposits/',re.I)
HREF=re.compile(r'terms|tnc|\bt-c\b|t&c|t_c|\btc\b|conditions|syarat|\.pdf',re.I)
TERMS=re.compile(r'terms|t\s?&\s?c|tnc|\bt-c\b|\btc\b|conditions|syarat',re.I)
STOP=set('the and with for your you on at of to in a an by up off get enjoy card cards credit pb cimb hlb uob dbs ocbc citi hsbc sc maybank ambank alliance aeon rhb bank promotion promotions privileges privilege offer offers deals deal campaign html page en my sg personal latest promo'.split())
def toks(s): return {w for w in re.findall(r'[a-z0-9]+',s.lower()) if len(w)>2 and w not in STOP and not w.isdigit()}
def strip_chrome(b): return re.sub(r'(?is)<(header|footer|nav)\b.*?</\1>',' ',b)
def tc_links(b,base):
    out=[]
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',b,flags=re.S|re.I):
        h=urllib.parse.urljoin(base,H.unescape(m.group(1).strip())); t=' '.join(H.unescape(re.sub('<[^>]+>',' ',m.group(2))).split())
        if h.startswith('http') and HREF.search(urllib.parse.unquote(h)) and TERMS.search(h+' '+t) and not GENERIC.search(h.split('?')[0]) and not re.search(r'privacy|general|governing|website|electronic|cookie',t,re.I):
            out.append((h,t))
    seen={h for h,_ in out}
    for m in re.finditer(r'(?:href|src|data-[a-z-]+)\s*=\s*["\']([^"\'#]+?\.pdf[^"\'#]*)["\']',b,flags=re.I):
        h=urllib.parse.urljoin(base,H.unescape(m.group(1).strip()))
        fn=urllib.parse.unquote(urllib.parse.urlparse(h).path.split('/')[-1])
        if h not in seen and re.search(r'(?:^|[^a-z])(?:tc|tnc|t&c|t-c|terms|tncs|syarat)(?:[^a-z]|$)',fn,re.I) and not GENERIC.search(h.split('?')[0]):
            out.append((h,'')); seen.add(h)
    return out
def main_text(b,title):
    t=visible_text(strip_chrome(b)); k=(title or '')[:25]
    i=t.find(k) if k else -1
    return t[i:] if i>=0 else t
def score(h,t,o):
    s=0; ot=toks(o['title']+' '+urllib.parse.urlparse(o['source_url']).path)
    ht=toks(urllib.parse.unquote(urllib.parse.urlparse(h).path)+' '+t)
    s+=2*len(ot&ht)
    if h.lower().split('?')[0].endswith('.pdf'): s+=1
    if re.search(r'terms|t&c|tnc',t,re.I): s+=1
    return s
def relevance(txt,o):
    ot=toks(o['title'])
    if not ot: return 0.0
    tl=' '+' '.join(re.findall(r'[a-z0-9]+',txt.lower()))+' '
    return sum(1 for w in ot if ' '+w+' ' in tl)/len(ot)
def own_section(text,o):
    """For a shared T&C doc, keep clauses that mention the deal's merchant or title words; None if not isolatable."""
    cl=TM.clauses(text); ot=toks(o['title'])
    if not cl: return None
    return cl
def enrich(o):
    u=o['source_url']; rec={'source_url':u,'page_mode':'static'}
    m,b=fetch(u)
    mt=main_text(b,o['title']) if b else ''
    links=tc_links(b,m['final_url']) if b else []
    if (m['status']!=200 or len(mt)<800 or not (TM.period(mt) or links)):
        hm,hb=render(u)
        if hb and hm.get('status')==200:
            b=hb; rec['page_mode']='headless'; mt=main_text(b,o['title']); links=tc_links(b,hm['final_url']) or links
        elif m['status']!=200: rec['error']=f"page status {m['status']} / headless {hm.get('status')} {hm.get('error','')}"[:200]; return rec
    rec['page_text_len']=len(mt)
    dp=TM.distinct_periods(mt[:20000])
    last=urllib.parse.urlparse(u).path.rstrip('/').split('/')[-1]
    if len(dp)>=2 and re.search(r'deals|offers|discounts|index',o['title']+' '+last,re.I):
        rec['hub']=True; rec['terms']=None; rec['hub_periods']=len(dp)
        return rec
    links=sorted({h:t for h,t in links}.items(),key=lambda x:-score(x[0],x[1],o))
    rec['tc_candidates']=[h for h,_ in links[:5]]
    tc=None
    for h,t in links[:3]:
        dm,dt=doc(h)
        if dm['status']!=200 or not dt: continue
        if dm.get('kind')!='pdf' and not re.search(r'terms|tnc|\bt-c\b|t&c|t_c|conditions|syarat',urllib.parse.unquote(dm['final_url'].split('?')[0]),re.I):
            rec.setdefault('tc_rejected',[]).append({'url':h,'why':'html page is not a T&C document'}); continue
        if dm.get('kind')!='pdf' and re.search(r'<title>[^<]*(?:for clients|terms of access|website terms|general terms)',dt,re.I):
            rec.setdefault('tc_rejected',[]).append({'url':h,'why':'general bank terms, not deal terms'}); continue
        txt=dt if dm.get('kind')=='pdf' else visible_text(strip_chrome(dt))
        if len(txt)<300: continue
        if re.search(r'terms (?:and|&) conditions governing|general terms|cardmember agreement|card ?holder agreement|online banking and mobile banking|terms of use|client terms|universal terms|banking services',TM.flat(txt[:600]),re.I):
            rec.setdefault('tc_rejected',[]).append({'url':h,'why':'general bank terms, not deal terms'}); continue
        rel=relevance(txt,o)
        if rel<0.5 and not (score(h,t,o)>=3 and rel>=0.3): rec.setdefault('tc_rejected',[]).append({'url':h,'relevance':round(rel,2)}); continue
        tc={'url':dm['final_url'] if dm['final_url'].startswith('http') else h,'fetched_at':dm['fetched_at'],'kind':dm.get('kind'),'text':txt,'score':score(h,t,o)}
        break
    rec['terms']=None
    if tc:
        p=TM.period(tc['text'])
        rec['terms']={'url':tc['url'],'fetched_at':tc['fetched_at'],'kind':tc['kind'],'score':tc['score'],'hash':TM.sha(tc['text']),'clauses':TM.clauses(tc['text'])}
        if p: rec['period']=dict(p,source_url=tc['url'],source_kind='terms')
        ms=TM.min_spend(tc['text']); cp=TM.cap(tc['text'])
        if ms: rec['min_spend']={'text':ms,'source_url':tc['url']}
        if cp: rec['cap']={'text':cp,'source_url':tc['url']}
    if 'period' not in rec:
        p=TM.period(mt[:8000])
        if not p:
            # a line that is only a date range (HLB style '05 November 2025-14 November 2025')
            for l in mt[:4000].split('\n'):
                r=TM._range(l)
                if r and len(l.strip())-len(r[3])<20:
                    p={'valid_from':r[1].isoformat(),'valid_until':r[2].isoformat(),'text':l.strip()[:300],'start_basis':'stated'}; break
        if p: rec['period']=dict(p,source_url=u,source_kind='page')
    if 'min_spend' not in rec:
        ms=TM.min_spend(mt[:8000])
        if ms: rec['min_spend']={'text':ms,'source_url':u}
    if 'cap' not in rec:
        cp=TM.cap(mt[:8000])
        if cp: rec['cap']={'text':cp,'source_url':u}
    # inline T&C on the page itself (deal's own section)
    if not rec['terms']:
        i=re.search(r'(?:^|\n)(?:Terms (?:and|&) Conditions|T&Cs?|Terma dan Syarat)\s*:?[ \t]*(?=\n|[A-Z0-9])',mt[:12000])
        if i:
            sec=mt[i.end():i.end()+6000]
            j=re.search(r'\n(?:Copyright|\u00a9|Privacy|Related (?:promotions|deals|offers)|You (?:may|might) also like|Other (?:promotions|deals)|More (?:promotions|deals)|Back to top|Share this)|Click here for (?:more info|the full)|Apply Now|We use cookies|Find out more',sec)
            if j: sec=sec[:j.start()]
            j=re.search(r'Click here for (?:more info|the full)|Apply Now|We use cookies',sec)
            if j: sec=sec[:j.start()]
            if len(sec)>120 and TM.period(sec) and not re.search(r'governing|website',sec[:200],re.I):
                rec['terms']={'url':m.get('final_url') if str(m.get('final_url','')).startswith('http') else u,'fetched_at':m.get('fetched_at'),'kind':'page_section','score':None,'hash':TM.sha(sec),'clauses':TM.clauses(sec)}
    return rec
if __name__=='__main__':
    offers=json.load(open('raw/offers_built.json'))
    done=json.load(open(OUT)) if os.path.exists(OUT) and '--fresh' not in sys.argv else {}
    todo=[o for o in offers if o['sources'][0]['kind']=='issuer_promotion_page' and o['source_url'] not in done]
    only=[a for a in sys.argv[1:] if not a.startswith('--')]
    if only: todo=[o for o in todo if o['issuer_id'] in only]
    # one host at a time: group by host
    todo.sort(key=lambda o:urllib.parse.urlparse(o['source_url']).netloc)
    for n,o in enumerate(todo):
        try: done[o['source_url']]=enrich(o)
        except Exception as e: done[o['source_url']]={'source_url':o['source_url'],'error':str(e)[:200]}
        r=done[o['source_url']]
        print(n,o['issuer_id'],r.get('page_mode'),(r.get('period') or {}).get('valid_until'),(r.get('terms') or {}).get('url'),r.get('error',''),flush=True)
        if n%10==0: json.dump(done,open(OUT,'w'),ensure_ascii=False)
    json.dump(done,open(OUT,'w'),ensure_ascii=False); close()
