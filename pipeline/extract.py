import re,html as H
def visible_text(b):
    b=re.sub(r'(?is)<(script|style|noscript|svg|template)\b.*?</\1>',' ',b)
    b=re.sub(r'(?is)<!--.*?-->',' ',b)
    b=re.sub(r'(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|td|th|section|span)>','\n',b)
    t=H.unescape(re.sub(r'<[^>]+>',' ',b))
    lines=[' '.join(l.split()) for l in t.split('\n')]
    return '\n'.join(l for l in lines if l)
def meta(b,name):
    m=re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']*)'%re.escape(name),b,re.I) or \
      re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']%s["\']'%re.escape(name),b,re.I)
    return ' '.join(H.unescape(m.group(1)).split()) if m else None
def title(b):
    m=re.search(r'(?is)<title[^>]*>(.*?)</title>',b); return ' '.join(H.unescape(re.sub('<[^>]+>','',m.group(1))).split()) if m else None
def h1(b):
    for m in re.finditer(r'(?is)<h1[^>]*>(.*?)</h1>',b):
        t=' '.join(H.unescape(re.sub('<[^>]+>',' ',m.group(1))).split())
        if t: return t
    return None
NET=[('amex',r'american express|\bamex\b'),('visa',r'\bvisa\b'),('mastercard',r'master\s?card|world elite|\bworld\b(?= (mastercard|card))'),('unionpay',r'union\s?pay'),('jcb',r'\bjcb\b'),('diners',r'diners')]
def networks_in(s):
    s=s.lower(); out=[]
    for n,p in NET:
        if re.search(p,s): out.append(n)
    return out
TIERS=[('world_elite',r'world elite'),('infinite',r'infinite'),('signature',r'signature'),('world',r'\bworld\b'),('platinum',r'platinum'),('titanium',r'titanium'),('gold',r'\bgold\b'),('classic',r'classic'),('reserve',r'reserve'),('centurion',r'centurion')]
def tier_of(name):
    s=name.lower()
    for t,p in TIERS:
        if re.search(p,s): return t
    return None
def islamic(name):
    return bool(re.search(r'(-i\b|card-i|islamic|ikhwan|\bi\b$|-i$)',name,re.I))
CUR=r'(?:RM|S\$|SGD|MYR)\s?[\d,]+(?:\.\d+)?'
def sentences(text):
    for line in text.split('\n'):
        for s in re.split(r'(?<=[.;])\s+(?=[A-Z])',line):
            s=s.strip()
            if 8<len(s)<=300: yield s
LOUNGE_PROG=[('priority_pass','priority pass'),('loungekey','loungekey|lounge key'),('dragonpass','dragon ?pass'),('plaza_premium','plaza premium'),('mastercard_travel_pass','travel pass'),('visa_airport_companion','visa airport companion'),('malaysia_airlines_golden_lounge','golden lounge'),('mastercard_airport_experiences','airport experiences')]
def benefits(text):
    out=[]; seen=set()
    def add(t,s,details=None):
        k=(t,s)
        if k in seen: return
        seen.add(k); d={'type':t,'text':s}
        if details: d['details']=details
        out.append(d)
    for s in sentences(text):
        l=s.lower()
        if 'debit card' in l: continue
        if 'lounge' in l and re.search(r'access|visit|complimentary|free|unlimited|enjoy|\d',l):
            progs=[p for p,r in LOUNGE_PROG if re.search(r,l)]
            m=None
            for pat in [r'(?<!over )(?<!than )\b(\d+|unlimited)\s*x\s*(?:complimentary\s*|free\s*)?(?:access(?:es)?\s*(?:to\s*)?)?(?:selected\s*|participating\s*)?(?:airport\s*|vip\s*)?lounge',
                        r'(?<!over )(?<!than )\b(\d+|unlimited)\s*(?:complimentary|free)\s*(?:airport\s*|vip\s*)?lounge\s*(?:access|visits?|passes|entries)',
                        r'(?<!over )(?<!than )\b(\d+|unlimited)\s*(?:complimentary\s*|free\s*)?(?:airport\s*)?lounge\s*(?:access(?:es)?|visits?|passes|entries)\b',
                        r'(unlimited)\s*(?:complimentary\s*)?(?:access|visits)',
                        r'(?<!over )(?<!than )\b(\d+)\s*x\b']:
                m=re.search(pat,l)
                if m: break
            det={}
            if progs: det['programmes']=progs
            if m: det['visits']=m.group(1) if m.group(1)=='unlimited' else int(m.group(1))
            if 'guest' in l: det['guest_mentioned']=True
            ms=re.search(r'min(?:imum|\.)?\s*(?:spend|spending)[^.;]{0,40}?('+CUR+')',s,re.I)
            if ms: det['min_spend_text']=ms.group(0)
            add('lounge_access',s,det or None)
        if re.search(r'\d+(?:\.\d+)?\s?%\s*(cash\s?back|rebate)|cash\s?back of',l):
            rates=[float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s?%',l)]
            cap=re.search(r'cap(?:ped)?\s*(?:at)?\s*('+CUR+')',s,re.I)
            det={'rates_pct':rates}
            if cap: det['cap_text']=cap.group(1)
            add('cashback',s,det)
        if re.search(r'\bmiles?\b',l) and re.search(r'\d',l) and re.search(r'per|every|for each|=|\bmpd\b',l):
            add('miles',s)
        elif re.search(r'(points?|treatspoints|bonuslink|enrich points)',l) and re.search(r'\d+\s?x\b|\bx\s?\d+|\d+\s+(?:\w+\s){0,3}points?\s+(?:for|per|on|with)',l):
            add('points',s)
        if 'travel insurance' in l or 'travel takaful' in l or 'travel accident' in l:
            m=re.search(CUR,s); add('travel_insurance',s,{'coverage_text':m.group(0)} if m else None)
        if 'golf' in l and re.search(r'green fee|golf club|golf course|complimentary|discount|off',l): add('golf',s)
        if re.search(r'\b(petrol|fuel)\b',l) and re.search(r'\d',l) and re.search(r'cash\s?back|rebate|saving|points|discount|off',l): add('fuel',s)
        if re.search(r'dining|restaurant',l) and re.search(r'\d+\s?%\s*(off|discount)',l): add('dining',s)
        if re.search(r'(0\s?%|zero).{0,20}(instalment|installment|easy payment|epp|ipp)',l): add('instalment',s)
        if re.search(r'annual fee',l) and re.search(r'waive|free|'+CUR.replace('\\','\\\\')[:0]+r'rm|s\$|nil|no annual',l): add('annual_fee_waiver',s)
    return out
def min_income(text):
    for pat in [r'min(?:imum|\.)?\s*(?:annual\s*)?income[^\n]{0,40}?((?:RM|S\$|SGD|MYR)\s?[\d,]+(?:\.\d+)?(?:\s*(?:p\.?a\.?|per annum|a year|annually|per month|monthly|/month|/year))?)',
                r'pendapatan minimum[^\n]{0,20}?(RM\s?[\d,]+(?:\s*setahun)?)',
                r'income of[^\n]{0,20}?((?:RM|S\$)\s?[\d,]+(?:\s*(?:p\.?a\.?|per annum|a year|annually))?)']:
        m=re.search(pat,text,re.I)
        if m: return {'text':' '.join(m.group(0).split())[:160],'amount_text':m.group(1)}
    return None
def annual_fee(text):
    for pat in [r'annual fees?[^\n]{0,15}?(?:principal[^\n]{0,15}?)?[:\-]?\s*((?:RM|S\$|SGD)\s?[\d,]+(?:\.\d+)?)[^\n]{0,80}',
                r'annual fees?[^\n]{0,60}?(free for life|waived for life|lifetime|no annual fee|free)[^\n]{0,60}',
                r'(free for life|no annual fee|lifetime annual fee waiver)[^\n]{0,60}']:
        m=re.search(pat,text,re.I)
        if m: return {'text':' '.join(m.group(0).split())[:200]}
    return None
