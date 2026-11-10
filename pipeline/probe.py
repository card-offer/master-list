import sys,json; sys.path.insert(0,'pipeline'); from fetch import fetch
from concurrent.futures import ThreadPoolExecutor
urls=[l.split()[-1] for l in open(sys.argv[1]) if l.strip()]
def f(u):
    m,b=fetch(u); return f"{m['status']} {len(b):>8} {u} -> {m['final_url']}"
with ThreadPoolExecutor(16) as ex:
    for r in ex.map(f,urls): print(r,flush=True)
