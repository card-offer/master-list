"""Worksheet helper: /workspace/cc-master/worksheet/sources.csv. Atomic save after every change."""
import csv,os,datetime,tempfile
P='worksheet/sources.csv'
COLS=['country','bank','source_url','page_type','status','cards_found','offers_found','date_checked','last_verified','notes_blockers']
def now(): return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
def load():
    if not os.path.exists(P): return []
    return list(csv.DictReader(open(P,newline='')))
def save(rows):
    fd,tmp=tempfile.mkstemp(dir='worksheet',suffix='.tmp')
    with os.fdopen(fd,'w',newline='') as f:
        w=csv.DictWriter(f,COLS); w.writeheader()
        for r in rows: w.writerow({k:str(r.get(k,'') or '').replace('\u2014',' - ') for k in COLS})
    os.replace(tmp,P)
import fcntl
def upd(url,**kw):
    with open('worksheet/.ws.lock','w') as lf:
        fcntl.flock(lf,fcntl.LOCK_EX)
        return _upd(url,**kw)
def _upd(url,**kw):
    rows=load(); hit=False
    for r in rows:
        if r['source_url']==url: r.update({k:v for k,v in kw.items()}); hit=True
    if not hit: rows.append({'source_url':url,**kw})
    save(rows); return hit
