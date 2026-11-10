"""Promotion period, minimum spend, cap and clause extraction from an offer's own T&C or page text.
Only dates written in the document are returned. Nothing is inferred beyond filling a missing
month or year inside one written range (for example '1 - 31 Dec 2026')."""
import json,os,re,datetime,hashlib
def _max_promotion_days():
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','config','rules.json')
    with open(path,encoding='utf-8') as fh:
        return json.load(fh)['max_promotion_days']
MONTHS={'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
 'januari':1,'februari':2,'mac':3,'mei':5,'jun':6,'julai':7,'ogos':8,'oktober':10,'disember':12}
for k,v in list(MONTHS.items()):
    if len(k)>3: MONTHS.setdefault(k[:3],v)
MONTHS['sept']=9; MONTHS['ogo']=8; MONTHS['dis']=12; MONTHS['okt']=10
M='(?:'+'|'.join(sorted(MONTHS,key=len,reverse=True))+r')\.?'
D=r'(\d{1,2})(?:st|nd|rd|th)?'
Y=r'(20\d\d)'
SEP=r'\s*(?:-|\u2013|\u2014|to|until|till|through|hingga|sehingga|sampai|and|&)\s*'
def _mk(y,mo,d):
    try: return datetime.date(int(y),int(mo),int(d))
    except Exception: return None
def _mon(s): return MONTHS.get(s.lower().rstrip('.')) if s else None
# ranges, most specific first
RANGES=[
 # 1 Oct 2026 to 31 Dec 2026 / 1 Oct to 31 Dec 2026 / 1 to 31 Dec 2026
 (re.compile(D+r'(?:\s+('+M+r'))?(?:\s*,?\s*'+Y+r')?\s*(?:\([^)]{0,20}\))?'+SEP+D+r'\s+('+M+r')\s*,?\s*'+Y,re.I),'dmy'),
 # October 1, 2026 to December 31, 2026 / October 1 to December 31, 2026
 (re.compile(r'('+M+r')\s+'+D+r'(?:\s*,?\s*'+Y+r')?'+SEP+r'(?:('+M+r')\s+)?'+D+r'\s*,?\s*'+Y,re.I),'mdy'),
 # 01/10/2026 - 31/12/2026, 01.10.2026 to 31.12.2026
 (re.compile(r'(\d{1,2})[/.](\d{1,2})[/.]'+Y+SEP+r'(\d{1,2})[/.](\d{1,2})[/.]'+Y),'num'),
]
SINGLE=[re.compile(D+r'\s+('+M+r')\s*,?\s*'+Y,re.I),re.compile(r'('+M+r')\s+'+D+r'\s*,?\s*'+Y,re.I),re.compile(r'\b(\d{1,2})[/.](\d{1,2})[/.]'+Y+r'\b')]
def _single(s):
    out=[]
    for i,p in enumerate(SINGLE):
        for m in p.finditer(s):
            g=m.groups()
            d=_mk(g[2],_mon(g[1]),g[0]) if i==0 else _mk(g[2],_mon(g[0]),g[1]) if i==1 else _mk(g[2],g[1],g[0])
            if d: out.append((m.start(),m.end(),d,m.group(0)))
    return sorted(out)
def _ranges(s):
    out=[]
    for p,kind in RANGES:
        for m in p.finditer(s):
            r=_range(m.group(0))
            if r: out.append((m.start(),m.end(),r[1],r[2],m.group(0)))
    for m in CE.finditer(s):
        a=_single(m.group(1)); b=_single(m.group(2))
        if a and b and a[0][2]<=b[0][2]: out.append((m.start(),m.end(),a[0][2],b[0][2],m.group(0)))
    return out
def _range(s):
    best=None
    for p,kind in RANGES:
        for m in p.finditer(s):
            g=m.groups()
            if kind=='dmy':
                d1,m1,y1,d2,m2,y2=g; mo2=_mon(m2); mo1=_mon(m1) or mo2
                yy1=y1 or (int(y2)-1 if mo1>mo2 else y2)
                a,b=_mk(yy1,mo1,d1),_mk(y2,mo2,d2)
            elif kind=='mdy':
                m1,d1,y1,m2,d2,y2=g; mo1=_mon(m1); mo2=_mon(m2) or mo1
                yy1=y1 or (int(y2)-1 if mo1>mo2 else y2)
                a,b=_mk(yy1,mo1,d1),_mk(y2,mo2,d2)
            else:
                a,b=_mk(g[2],g[1],g[0]),_mk(g[5],g[4],g[3])
            if a and b and a<=b and (b-a).days<=_max_promotion_days():
                if best is None or m.start()<best[0]: best=(m.start(),a,b,m.group(0))
    return best
CE=re.compile(r'(?:commenc\w*|start\w*|begin\w*|run\w*)\s+(?:on|from)\s+(.{6,30}?20\d\d)\b[^.;]{0,80}?\b(?:end\w*|until|till|to|expir\w*)\s+(?:on\s+)?(.{6,30}?20\d\d)\b',re.I)
STRONG=re.compile(r'(?:promotion|promotional|campaign|programme|program|contest|offer|event|qualifying|redemption|deal|privilege|sale)s?\s+period|tempoh\s+(?:promosi|kempen|program)|both dates inclusive|(?:valid|available|runs?|running|applicable|effective)\s+(?:from|between|until|till|through|thru|up to|on)|(?:promotion|campaign|offer|programme|deal)s?\s+(?:is |are |will be )?(?:valid|available|runs?|starts?|ends?|from|between)|from\s+now\s+(?:until|till|to)|\bends?\s+on\b|\bexpir(?:es|y|ing)\b|\bon or before\b|\buntil\b|\btill\b|sehingga|hingga',re.I)
END_ONLY=re.compile(r'(?:until|till|through|thru|up to|ends? on|expir\w* on|on or before|valid through|sehingga|hingga|no later than|by)\s*(?:and including\s*)?$',re.I)
START_ONLY=re.compile(r'(?:from|starting|starts? on|commenc\w*|effective)\s*$',re.I)
NOISE=re.compile(r'approved on or before|approved before|applications? (?:approved|submitted)|last (?:updated|modified|revised)|published|copyright|registration no|\(\d{6}-[A-Z]\)|revised on|version|effective date of these|dated',re.I)
def distinct_periods(text):
    t=flat(text); return {(r[2],r[3]) for r in _ranges(t)}
def flat(t): return re.sub(r'\s+',' ',t.replace('\u00a0',' ')).strip()
def period(text):
    """Return dict(valid_from, valid_until, text) for the first strongly worded promotion period, else None."""
    t=flat(text)
    hits=[]
    for m in STRONG.finditer(t):
        strong=bool(re.search('period|tempoh|inclusive',m.group(0),re.I))
        lo=max(0,m.start()-(220 if strong else 40)); w=t[lo:m.end()+260]
        if NOISE.search(t[max(0,m.start()-40):m.end()+80]): continue
        rs=_ranges(w)
        if rs:
            k=m.start()-lo
            best=min(rs,key=lambda r:0 if r[0]<=k<=r[1]+5 else min(abs(r[0]-k),abs(r[1]-k)))
            a,b=best[2],best[3]
            if (b-a).days>_max_promotion_days(): continue
            hits.append((0 if strong else 1,m.start(),{'valid_from':a.isoformat(),'valid_until':b.isoformat(),'text':flat(t[max(0,lo+best[0]-80):lo+best[1]+80])[:300],'start_basis':'stated'}))
            continue
        # end-only or start-only phrase directly followed by one date
        tail=t[m.start():m.end()+80]
        ss=_single(tail)
        if ss and END_ONLY.search(tail[:ss[0][0]].strip()) :
            hits.append((2,m.start(),{'valid_from':None,'valid_until':ss[0][2].isoformat(),'text':t[max(0,m.start()-60):m.end()+120].strip()[:300],'start_basis':'not_stated'}))
    if not hits: return None
    hits.sort(key=lambda h:(h[0],h[1]))
    return hits[0][2]
CUR=r'(?:RM|S\$|SGD|MYR|\$)\s?[\d,]+(?:\.\d+)?'
def min_spend(text):
    t=flat(text)
    m=re.search(r'(?:min(?:imum|\.)?\s+(?:single\s+|accumulated\s+|cumulative\s+|nett\s+|total\s+|eligible\s+|qualifying\s+)*(?:receipt\s+|retail\s+|card\s+)?(?:spend(?:ing)?|purchase|transaction|bill|amount)s?(?:\s+amount)?(?:\s+of)?)\s*(?:\w+\s){0,3}?'+CUR,t,re.I) or \
      re.search(r'(?:spend|charge)s?\s+(?:a\s+)?(?:min(?:imum|\.)?\s+(?:of\s+)?)'+CUR,t,re.I)
    return m.group(0)[:200] if m else None
def cap(text):
    t=flat(text)
    m=re.search(r'(?:capped at|cap(?:ped)? of|maximum (?:of )?(?:cash ?back|rebate|discount|reward|bonus|savings?)[^.]{0,40}?|up to a maximum of|limited to a maximum of|subject to a (?:maximum|cap) of)\s*'+CUR+r'[^.;]{0,80}',t,re.I) or \
      re.search(r'(?:limited to|capped at|maximum of)\s+(?:the first\s+)?[\d,]+\s+(?:redemptions?|vouchers?|codes?|cardmembers?|cardholders?|customers?)[^.;]{0,60}',t,re.I)
    return m.group(0)[:240] if m else None
def clauses(text):
    """Split T&C text into numbered clauses. Returns list of {n, text}."""
    lines=[l.strip() for l in text.replace('\r','').split('\n')]
    out=[]; cur=None
    NUM=re.compile(r'^((?:\d{1,2}(?:\.\d{1,2}){0,3})\.?|\([a-z]{1,4}\)|[a-z]\)|\([0-9]{1,2}\))\s+(\S.*)$')
    for l in lines:
        if not l: continue
        m=NUM.match(l)
        if m and not re.match(r'^\d{1,2}\s+(?:'+M+r')',l,re.I):
            if cur: out.append(cur)
            cur={'n':m.group(1).rstrip('.'),'text':m.group(2)}
        elif cur: cur['text']+=' '+l
        else: cur={'n':None,'text':l}
    if cur: out.append(cur)
    for c in out: c['text']=flat(c['text']).replace('\u2014',' - ')
    return [c for c in out if len(c['text'])>3]
def norm_for_hash(text): return flat(text).lower()
def sha(text): return hashlib.sha256(norm_for_hash(text).encode()).hexdigest()
