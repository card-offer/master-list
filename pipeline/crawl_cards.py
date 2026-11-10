import sys,re,json; sys.path.insert(0,'pipeline'); from fetch import fetch; from links import links
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
cfg=json.load(open('pipeline/issuers_config.json'))
BAD=re.compile(r'promo|faq|terms|tnc|apply|form|calculator|compare|comparator|feature|service|supplementary|debit|prepaid|business|corporate|commercial|biz|balance-transfer|instalment|installment|easi|flexi|payment|lounge|guide|learn|reward(s)?-(programme|catalog)|activation|pin|statement|google|apple|samsung|garmin|alipay|click-to-pay|wallet|/bm/|/ms/|/zh|/cn/',re.I)
def run(iss):
    pat=re.compile(iss['product'],re.I); host={urllib.parse.urlparse(s).netloc for s in iss['seeds']}
    found=set()
    for s in iss['seeds']:
        try:
            for h in links(s):
                if urllib.parse.urlparse(h).netloc in host and pat.search(urllib.parse.urlparse(h).path) and not BAD.search(h): found.add(h)
        except Exception as e: print(iss['id'],'ERR',e)
    # sitemap candidates
    try:
        cc,b=iss['id'].split('-',1)
        for f in [f"raw/sitemap_{cc}_{b.split('-')[0]}.txt"]:
            for h in open(f).read().split():
                if urllib.parse.urlparse(h).netloc in host and pat.search(urllib.parse.urlparse(h).path) and not BAD.search(h): found.add(h.split('?')[0])
    except FileNotFoundError: pass
    for h in sorted(found): fetch(h)
    return iss['id'],sorted(found)

only=set(sys.argv[1:])
cfg=[c for c in cfg if not only or c['id'] in only]
old=json.load(open('raw/card_candidates.json')) if __import__('os').path.exists('raw/card_candidates.json') else {}
res=old
with ThreadPoolExecutor(10) as ex:
    for k,v in ex.map(run,cfg): res[k]=v; print(k,len(v),flush=True)
json.dump(res,open('raw/card_candidates.json','w'),indent=1)
