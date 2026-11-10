"""Headless (Playwright) and document fetchers. Same politeness rules as fetch.py:
one host at a time, at least 1.5 s between requests to a host, everything cached under raw/cache/."""
import hashlib,json,os,time,urllib.parse,subprocess,datetime,re
CACHE='raw/cache'; HC=CACHE+'/headless'; DC=CACHE+'/docs'
for d in (HC,DC): os.makedirs(d,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DELAY=1.5; _last={}
def key(u): return hashlib.sha1(u.encode()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
def _wait(u):
    h=urllib.parse.urlparse(u).netloc; w=_last.get(h,0)+DELAY-time.time()
    if w>0: time.sleep(w)
    _last[h]=time.time()
_pw=None; _br=None
def _browser():
    global _pw,_br
    if _br is None:
        from playwright.sync_api import sync_playwright
        _pw=sync_playwright().start(); _br=_pw.chromium.launch()
    return _br
def render(u,force=False,wait_ms=2500,timeout=40000):
    """Rendered DOM HTML of a page. Returns (meta, html)."""
    k=key(u); mp=f'{HC}/{k}.json'; hp=f'{HC}/{k}.html'
    if os.path.exists(mp) and not force:
        return json.load(open(mp)),(open(hp,errors='ignore').read() if os.path.exists(hp) else '')
    _wait(u); m={'url':u,'status':0,'final_url':u,'fetched_at':now(),'mode':'headless'}; html=''
    try:
        ctx=_browser().new_context(user_agent=UA,locale='en-GB'); pg=ctx.new_page()
        r=pg.goto(u,timeout=timeout,wait_until='domcontentloaded')
        try: pg.wait_for_load_state('networkidle',timeout=15000)
        except Exception: pass
        pg.wait_for_timeout(wait_ms)
        html=pg.content(); m['status']=r.status if r else 0; m['final_url']=pg.url; ctx.close()
    except Exception as e: m['error']=str(e)[:300]
    open(hp,'w').write(html); json.dump(m,open(mp,'w'))
    return m,html
def doc(u,force=False,timeout=40):
    """Fetch a T&C document. PDFs are converted with pdftotext. Returns (meta, text_or_html)."""
    k=key(u); mp=f'{DC}/{k}.json'; bp=f'{DC}/{k}.bin'; tp=f'{DC}/{k}.txt'
    if os.path.exists(mp) and not force:
        m=json.load(open(mp)); return m,(open(tp,errors='ignore').read() if os.path.exists(tp) else '')
    _wait(u)
    r=subprocess.run(['curl','-sL','--compressed','-A',UA,'--max-time',str(timeout),'-o',bp,'-w','%{http_code} %{content_type} %{url_effective}',u],capture_output=True,text=True)
    p=(r.stdout or '000 - '+u).split(' ',2)
    m={'url':u,'status':int(p[0]) if p[0].isdigit() else 0,'content_type':p[1] if len(p)>1 else '','final_url':p[2] if len(p)>2 else u,'fetched_at':now()}
    txt=''
    if os.path.exists(bp):
        head=open(bp,'rb').read(5)
        if head.startswith(b'%PDF'):
            m['kind']='pdf'; subprocess.run(['pdftotext','-q',bp,tp]); txt=open(tp,errors='ignore').read() if os.path.exists(tp) else ''
        else:
            m['kind']='html'; txt=open(bp,errors='ignore').read(); open(tp,'w').write(txt)
    json.dump(m,open(mp,'w'))
    return m,txt
def close():
    global _pw,_br
    if _br: _br.close(); _pw.stop(); _br=None; _pw=None
