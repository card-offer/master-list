import sys,re,html,urllib.parse; sys.path.insert(0,'pipeline'); from fetch import fetch
def links(u):
    m,b=fetch(u); base=m['final_url']; out={}
    for mm in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>',b,flags=re.S|re.I):
        h=urllib.parse.urljoin(base,html.unescape(mm.group(1).strip())).split('?')[0]
        t=' '.join(html.unescape(re.sub(r'<[^>]+>',' ',mm.group(2))).split())
        if h not in out or (len(t)>len(out[h]) and len(t)<120): out[h]=t
    return out
if __name__=='__main__':
    pat=re.compile(sys.argv[2],re.I)
    for h,t in sorted(links(sys.argv[1]).items()):
        if pat.search(h): print(h,'|',t[:80])
