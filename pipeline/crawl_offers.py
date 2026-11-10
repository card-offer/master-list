import sys,re,json,urllib.parse,os; sys.path.insert(0,'pipeline'); from fetch import fetch; from links import links
from concurrent.futures import ThreadPoolExecutor
cfg=json.load(open('pipeline/offers_config.json')); CAP=150
BAD=re.compile(r'\.pdf$|/bm/|/ms/|/zh|/cn/|winner|faq|form|application-leads|/business',re.I)
only=set(sys.argv[1:])
def run(item):
    iss,c=item; pat=re.compile(c['pat']); host={urllib.parse.urlparse(s).netloc for s in c['seeds']}
    found=[]
    def ok(h):
        p=urllib.parse.urlparse(h); return p.netloc in host and pat.search(p.path) and not BAD.search(h)
    for s in c['seeds']:
        try:
            for h in links(s):
                if ok(h) and h not in found and h not in c['seeds']: found.append(h)
        except Exception as e: print(iss,'ERR',e)
    if c.get('sitemap') and os.path.exists(f"raw/sitemap_{c['sitemap']}.txt"):
        for h in open(f"raw/sitemap_{c['sitemap']}.txt").read().split():
            h=h.split('?')[0]
            if ok(h) and h not in found: found.append(h)
    # one level deeper from category pages (listing pages linking to more promos)
    for h in list(found)[:20]:
        try:
            for h2 in links(h):
                if ok(h2) and h2 not in found and len(found)<CAP: found.append(h2)
        except Exception: pass
    found=found[:CAP]
    for h in found: fetch(h)
    return iss,found
out=json.load(open('raw/offer_candidates.json')) if os.path.exists('raw/offer_candidates.json') else {}
items=[(k,v) for k,v in cfg.items() if not only or k in only]
with ThreadPoolExecutor(18) as ex:
    for k,v in ex.map(run,items): out[k]=v; print(k,len(v),flush=True)
json.dump(out,open('raw/offer_candidates.json','w'),indent=1)
