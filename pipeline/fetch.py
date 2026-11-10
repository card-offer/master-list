"""Polite cached fetcher. Cache: raw/cache/<sha1>.html + raw/cache/index.jsonl"""
import hashlib,json,os,time,threading,urllib.parse,subprocess,datetime
CACHE='raw/cache'; os.makedirs(CACHE,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
_last={}; _lock=threading.Lock(); DELAY=1.5
def key(u): return hashlib.sha1(u.encode()).hexdigest()
def meta(u):
    p=f'{CACHE}/{key(u)}.json'
    return json.load(open(p)) if os.path.exists(p) else None
def fetch(u,force=False,timeout=25):
    m=meta(u)
    if m and not force:
        body=open(f'{CACHE}/{key(u)}.html',errors='ignore').read() if os.path.exists(f'{CACHE}/{key(u)}.html') else ''
        return m,body
    host=urllib.parse.urlparse(u).netloc
    with _lock:
        w=_last.get(host,0)+DELAY-time.time()
        _last[host]=max(time.time(),_last.get(host,0)+DELAY)
    if w>0: time.sleep(w)
    out=f'{CACHE}/{key(u)}.html'
    r=subprocess.run(['curl','-sL','--compressed','-A',UA,'--max-time',str(timeout),'-o',out,'-w','%{http_code} %{url_effective}',u],capture_output=True,text=True)
    parts=(r.stdout or '000 '+u).split(' ',1)
    m={'url':u,'status':int(parts[0]) if parts[0].isdigit() else 0,'final_url':parts[1] if len(parts)>1 else u,
       'fetched_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')}
    json.dump(m,open(f'{CACHE}/{key(u)}.json','w'))
    body=open(out,errors='ignore').read() if os.path.exists(out) else ''
    return m,body
