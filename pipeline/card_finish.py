"""Card clean-up at publish time: one structured entry per benefit type, heading-only lines dropped,
numeric annual fee, minimum income, earn rates and waiver rules. Values come only from the page text
already captured for the card; anything not stated stays null."""
import re
NUM=r'([\d,]+(?:\.\d+)?)'
CUR=r'(?:RM|S\$|SGD|MYR|\$)\s?'
def heading_only(t):
    t=t.strip(' .:-*')
    w=t.split()
    if not w: return True
    if re.search(r'\d',t): return False
    if len(w)<=5 and not re.search(r'[.,;!]',t): return True
    return False
def num(s): return float(s.replace(',',''))
CATKW=[('overseas',r'overseas|foreign currency|abroad|international'),('online',r'online|e-?commerce'),('dining',r'dining|restaurant|food'),
 ('groceries',r'grocer|supermarket'),('petrol',r'petrol|fuel'),('travel',r'travel|airline|flight|hotel'),('ewallet',r'e-?wallet'),
 ('utilities',r'utilit|bill'),('contactless',r'contactless|paywave|tap'),('local',r'local'),('entertainment',r'cinema|movie|entertainment'),
 ('transport',r'transport|ride|grab|gojek'),('shopping',r'shopping|retail|department'),('all_spend',r'all (?:other )?(?:eligible )?(?:retail )?(?:spend|purchases|transactions)|every|any (?:retail )?(?:spend|purchase)|other spend|all other')]
def cats(phrase):
    p=phrase.lower(); out=[c for c,k in CATKW if re.search(k,p)]
    return out or ['unspecified']
def earn_rates(texts):
    out=[]; seen=set()
    for t in texts:
        for m in re.finditer(r'(?:up to\s+)?(\d+(?:\.\d+)?)\s?%\s*(?:cash\s?back|cash rebate|rebate)\s*(?:on|for|when you spend on|at)?\s*([^.;!()]{0,90})',t,re.I):
            for c in cats(m.group(2)):
                k=('cashback_pct',c,float(m.group(1)))
                if k not in seen: seen.add(k); out.append({'kind':'cashback_pct','category':c,'rate':float(m.group(1)),'up_to':m.group(0).lower().startswith('up to'),'text':m.group(0).strip()[:160]})
        for m in re.finditer(r'(?:up to\s+)?(\d+(?:\.\d+)?)\s?x\s*(?:\w+\s){0,2}?(?:points|treats points|rewards points|bonus points)\s*(?:on|for|when you spend on|at)?\s*([^.;!()]{0,90})',t,re.I):
            for c in cats(m.group(2)):
                k=('points_multiplier',c,float(m.group(1)))
                if k not in seen: seen.add(k); out.append({'kind':'points_multiplier','category':c,'rate':float(m.group(1)),'up_to':m.group(0).lower().startswith('up to'),'text':m.group(0).strip()[:160]})
        for m in re.finditer(r'(?:up to\s+)?(\d+(?:\.\d+)?)\s*(?:air\s?)?miles?\s*(?:per|for every|with every)\s*'+CUR+r'?(\d+(?:\.\d+)?)\s*(?:spent|spend)?\s*(?:on|for)?\s*([^.;!()]{0,90})',t,re.I):
            for c in cats(m.group(3)):
                k=('miles_per_currency_unit',c,float(m.group(1)))
                if k not in seen: seen.add(k); out.append({'kind':'miles_per_currency_unit','category':c,'rate':round(float(m.group(1))/float(m.group(2)),4),'up_to':m.group(0).lower().startswith('up to'),'text':m.group(0).strip()[:160]})
        for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:\w+\s){0,2}?points?\s*(?:per|for every|with every)\s*'+CUR+r'(\d+(?:\.\d+)?)\s*(?:spent|spend)?\s*(?:on|for)?\s*([^.;!()]{0,90})',t,re.I):
            for c in cats(m.group(3)):
                k=('points_per_currency_unit',c,float(m.group(1)))
                if k not in seen: seen.add(k); out.append({'kind':'points_per_currency_unit','category':c,'rate':round(float(m.group(1))/float(m.group(2)),4),'up_to':False,'text':m.group(0).strip()[:160]})
    spec={(r['kind'],r['rate']) for r in out if r['category']!='unspecified'}
    return [r for r in out if not (r['category']=='unspecified' and (r['kind'],r['rate']) in spec)]
def lounge(texts,progs):
    visits=[]; guest=None; supp=None
    for t in texts:
        l=t.lower()
        for m in re.finditer(r'(\d{1,2})\s*(?:x\s*)?(?:complimentary\s+|free\s+)?(?:\w+\s){0,3}?(?:lounge\s+)?(?:access(?:es)?|visits?|entr(?:y|ies)|passes)',l):
            n=int(m.group(1))
            if 0<n<=50 and n not in visits: visits.append(n)
        if 'unlimited' in l and 'lounge' in l and 'unlimited' not in visits: visits.append('unlimited')
        if re.search(r'guest|companion|accompan',l):
            guest=(guest+' | ' if guest else '')+t.strip()[:200] if not guest or len(guest)<400 else guest
        if re.search(r'supplementary',l) and 'lounge' in l or re.search(r'supplementary.{0,80}(visit|access)',l):
            if re.search(r'shared|combined|in total|between (?:the )?principal and supplementary|inclusive of supplementary',l): supp=True
            elif re.search(r'(?:each|own|separate|individual)\b.{0,60}supplementary|supplementary.{0,60}(?:each|own|separate|also entitled|entitled to their own)',l): supp=False
    return {'programmes':sorted(progs),'visits':visits[0] if len(visits)==1 else None,'visits_values':visits,'guest_policy_text':guest,'supplementary_share_visits':supp}
def fee(card,waiver_texts):
    af=card.get('annual_fee'); out=None
    if af:
        t=af['text']; out={'text':t,'source_url':af['source_url'],'amount':None,'principal_amount':None,'supplementary_amount':None,'waiver_rules':[]}
        l=t.lower()
        if re.search(r'\b(no|free|waived?|nil)\b.{0,15}annual fee|annual fee\s*:?\s*(free|nil|waived)|free for life|lifetime (annual )?fee waiver',l): out['amount']=0.0
        m=re.search(CUR+NUM,t)
        if m and out['amount'] is None: out['amount']=num(m.group(1))
        pm=re.search(r'principal[^.;]{0,40}?'+CUR+NUM,t,re.I); sm=re.search(r'supplementary[^.;]{0,40}?'+CUR+NUM,t,re.I)
        if pm: out['principal_amount']=num(pm.group(1))
        if sm: out['supplementary_amount']=num(sm.group(1))
        if pm and out['amount'] is None: out['amount']=out['principal_amount']
        waiver_texts=[t]+waiver_texts
    rules=[]
    for w in waiver_texts:
        l=w.lower()
        if not re.search(r'waiv|free|no annual fee',l): continue
        r={'text':w.strip()[:240],'kind':None,'min_spend':None,'min_transactions':None}
        if re.search(r'lifetime|for life|no annual fee|free for life|with no conditions',l): r['kind']='lifetime'
        if re.search(r'first year|1st year|first 1 year',l): r['kind']='first_year'
        ms=re.search(r'(?:spend|spending|usage)[^.;]{0,30}?'+CUR+NUM,w,re.I)
        if ms: r['min_spend']=num(ms.group(1)); r['kind']=r['kind'] or 'spend_based'
        mt=re.search(r'(\d{1,3})\s*(?:card\s+)?(?:swipes|transactions|times)',l)
        if mt: r['min_transactions']=int(mt.group(1)); r['kind']=r['kind'] or 'transaction_based'
        r['kind']=r['kind'] or 'conditional'
        if r['text'] not in [x['text'] for x in rules]: rules.append(r)
    if out is not None: out['waiver_rules']=rules
    elif rules: out={'text':None,'source_url':card['official_url'],'amount':None,'principal_amount':None,'supplementary_amount':None,'waiver_rules':rules}
    return out
def income(card):
    mi=card.get('min_income')
    if not mi: return None
    t=mi.get('amount_text') or mi['text']; m=re.search(CUR+NUM+r'\s*(k\b)?',t,re.I)
    amt=num(m.group(1))*(1000 if m and m.group(2) else 1) if m else None
    per='year' if re.search(r'annum|p\.a|year|annual',mi['text'],re.I) else 'month' if re.search(r'month|p\.m',mi['text'],re.I) else None
    return {'text':mi['text'],'source_url':mi['source_url'],'amount':amt,'period':per,'annual_amount':(amt if per=='year' else amt*12 if per=='month' and amt is not None else None)}
def finish(card):
    raw=card['benefits']; by={}
    for b in raw:
        b=dict(b,text=re.sub(r'^[\u2022\-*\s]+','',b['text']).strip())
        if heading_only(b['text']) or re.match(r'click here|find out more|learn more|apply now',b['text'],re.I): continue
        e=by.setdefault(b['type'],{'type':b['type'],'texts':[],'source_url':b['source_url'],'details':{}})
        if b['text'].lower().rstrip(' .') not in [x.lower().rstrip(' .') for x in e['texts']]: e['texts'].append(b['text'])
        d=b.get('details') or {}
        for k,v in d.items():
            if k=='rates_pct': e['details'].setdefault('rates_pct',[]); e['details']['rates_pct']=sorted(set(e['details']['rates_pct'])|set(v))
            elif k=='programmes': e['details'].setdefault('programmes',[]); e['details']['programmes']=sorted(set(e['details']['programmes'])|set(v))
            elif k not in e['details']: e['details'][k]=v
    progs={p for b in raw if b['type']=='lounge_access' for p in (b.get('details') or {}).get('programmes',[])}
    if 'lounge_access' in by:
        lt=[b['text'] for b in raw if b['type']=='lounge_access']
        L=lounge(lt,progs); by['lounge_access']['details'].update(L); by['lounge_access']['details'].pop('guest_mentioned',None)
        if isinstance(by['lounge_access']['details'].get('visits'),str): by['lounge_access']['details']['visits']=None
    rates=earn_rates([b['text'] for b in raw if b['type'] in ('cashback','points','miles','fuel','dining')])
    for e in by.values():
        e['text']=e['texts'][0]
        if not e['details']: e['details']=None
    card['benefits']=list(by.values())
    card['earn_rates']=[dict(r,source_url=card['official_url']) for r in rates]
    card['annual_fee']=fee(card,[b['text'] for b in raw if b['type']=='annual_fee_waiver'])
    card['min_income']=income(card)
    return card
