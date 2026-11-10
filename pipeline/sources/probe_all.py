import sys,json,re,urllib.parse; sys.path.insert(0,'pipeline'); sys.path.insert(0,'pipeline/sources')
from fetch import fetch; from seedlist import S
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
by=defaultdict(list)
for r in S: by[urllib.parse.urlparse(r[2]).netloc].append(r)
def run(rows):
    out=[]
    for cc,b,u,pt in rows:
        m,body=fetch(u,timeout=20)
        t=re.sub(r'<script.*?</script>|<style.*?</style>','',body,flags=re.S|re.I); t=re.sub(r'<[^>]+>',' ',t); words=len(t.split())
        out.append(dict(country=cc,bank=b,url=u,page_type=pt,status=m['status'],final=m['final_url'],bytes=len(body),words=words,
          credit=len(re.findall(r'credit card|kad kredit|credit-card',body,re.I))))
    return out
res=[]
with ThreadPoolExecutor(16) as ex:
    for o in ex.map(run,by.values()): res+=o
json.dump(res,open('raw/sources/probe.json','w'),indent=1)
for r in res: print(r['country'],r['bank'][:18].ljust(18),r['status'],r['bytes'],r['words'],r['credit'],r['url'],'->'+r['final'] if r['final']!=r['url'] else '')
