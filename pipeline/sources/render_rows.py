"""Render worksheet rows headless (static first), save visible text + links under raw/sources/text/. Sequential, polite."""
import sys,re,json,hashlib,html as H,urllib.parse; sys.path.insert(0,'pipeline'); sys.path.insert(0,'pipeline/sources')
import ws; from fetch import fetch; from hfetch import render,close; from extract import visible_text
def k(u): return hashlib.sha1(u.encode()).hexdigest()[:12]
def links_of(b,base):
    out={}
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',b,flags=re.S|re.I):
        h=urllib.parse.urljoin(base,H.unescape(m.group(1).strip())); t=' '.join(H.unescape(re.sub('<[^>]+>',' ',m.group(2))).split())
        if h.startswith('http') and (h not in out or len(t)>len(out[h])): out[h]=t[:150]
    return out
def get(u,force_headless=False):
    m,b=fetch(u); mode='static'
    t=visible_text(b) if b else ''
    if force_headless or m['status']!=200 or len(t.split())<400:
        hm,hb=render(u)
        if hb and len(visible_text(hb).split())>len(t.split()): m,b,mode=hm,hb,'headless'; t=visible_text(b)
    return m,b,t,mode
if __name__=='__main__':
    only=sys.argv[1:]
    for r in ws.load():
        u=r['source_url']
        if only and not any(o in u or o==r['bank'] for o in only): continue
        if not only and (r['status']!='to do' or r['page_type']=='tnc'): continue
        m,b,t,mode=get(u)
        open(f'raw/sources/text/{k(u)}.txt','w').write(f"URL {u}\nFINAL {m.get('final_url')}\nSTATUS {m.get('status')} MODE {mode}\n\n"+t)
        json.dump(links_of(b,m.get('final_url') or u),open(f'raw/sources/text/{k(u)}.links.json','w'),indent=0)
        print(r['country'],r['bank'],m.get('status'),mode,len(t.split()),k(u),u,flush=True)
    close()
