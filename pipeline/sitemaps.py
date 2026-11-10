import sys,re,json
sys.path.insert(0,'pipeline'); from fetch import fetch
from concurrent.futures import ThreadPoolExecutor
def locs(u,depth=0):
    m,b=fetch(u)
    L=re.findall(r'<loc>\s*([^<\s]+)\s*</loc>',b)
    out=[]
    for l in L:
        if l.endswith('.xml') and depth<2 and 'sitemap' in l.lower():
            out+=locs(l,depth+1)
        else: out.append(l)
    return out
seeds=json.load(open('pipeline/sitemap_seeds.json'))
def run(item):
    k,urls=item; allu=[]
    for u in urls:
        try: allu+=locs(u)
        except Exception as e: print(k,e)
    open(f'raw/sitemap_{k}.txt','w').write('\n'.join(sorted(set(allu))))
    print(k,len(set(allu)),flush=True)
with ThreadPoolExecutor(12) as ex: list(ex.map(run,seeds.items()))
