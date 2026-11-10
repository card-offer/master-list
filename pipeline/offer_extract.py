import re,datetime
MON={m:i for i,m in enumerate(['january','february','march','april','may','june','july','august','september','october','november','december'],1)}
MON.update({k[:3]:v for k,v in list(MON.items())}); MON['sept']=9
MS='(?:'+'|'.join(sorted(MON,key=len,reverse=True))+r')\.?'
DPAT=[re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+('+MS+r')\s*,?\s*(20\d\d)\b',re.I),
      re.compile(r'\b('+MS+r')\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(20\d\d)\b',re.I),
      re.compile(r'\b(\d{1,2})/(\d{1,2})/(20\d\d)\b')]
def dates_in(s):
    out=[]
    for i,p in enumerate(DPAT):
        for m in p.finditer(s):
            try:
                if i==0: d=datetime.date(int(m.group(3)),MON[m.group(2).lower().rstrip('.')],int(m.group(1)))
                elif i==1: d=datetime.date(int(m.group(3)),MON[m.group(1).lower().rstrip('.')],int(m.group(2)))
                else: d=datetime.date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
                out.append((m.start(),d))
            except Exception: pass
    return [d for _,d in sorted(out)]
CTX=re.compile(r'valid|period|until|till|from|ends?\b|between|expir|campaign|promotion|tempoh|sehingga|hingga',re.I)
def validity(text):
    best=None
    for line in text.split('\n'):
        if len(line)>400 or not CTX.search(line): continue
        ds=dates_in(line)
        if ds:
            best=(line.strip()[:240],min(ds),max(ds)) ; break
    if not best: return None
    line,a,b=best
    return {'text':line,'valid_from':a.isoformat() if a!=b else None,'valid_until':b.isoformat()}
CATS=[('balance_transfer',r'balance transfer'),('cash_plan',r'cash ?(xcess|on call|plan|advance|instalment)|easycash|flexi ?cash'),
 ('instalment',r'0\s?% (?:interest |easy ?payment |ezypay |instal)|instalment|installment|easy payment plan|\bepp\b|\bipp\b|ezypay'),
 ('sign_up',r'new card ?(member|holder)s?|sign[ -]?up|welcome (gift|offer|reward)|apply (now )?(and|&) (get|enjoy)|new-to-bank|new to bank'),
 ('petrol',r'petrol|fuel|\bshell\b|petronas|caltex|esso|\bbhp\b|petron'),('ev_charging',r'\bev\b|charging'),
 ('groceries',r'grocer|supermarket|hypermarket|aeon big|lotus|jaya grocer|fairprice|sheng siong|cold storage|giant'),
 ('ewallet',r'e-?wallet|touch .?n go|grabpay|boost|shopeepay'),
 ('hotel',r'hotel|resort|staycation|marriott|hilton|shangri|hyatt|accor|agoda|booking\.com|expedia'),
 ('travel',r'travel|flight|airline|airasia|malaysia airlines|singapore airlines|scoot|trip\.com|klook|overseas|holiday|\btours?\b'),
 ('dining',r'dining|restaurant|buffet|dine|food|bistro|kitchen|sushi|pizza|burger|steak|seafood|lunch|dinner|bar\b|grill|cuisine'),
 ('cafe',r'caf[eé]|coffee|kopitiam|bakery|tea\b|dessert|gelato|ice cream|waffle'),
 ('beauty',r'beauty|salon|spa\b|facial|\bhair\b|aesthetic|massage|perfume|cosmetic|skincare|wax'),
 ('health',r'medical|hospital|clinic|klinik|dental|pharma|health|wellness|optical'),
 ('electronics',r'phone|iphone|samsung|vivo|oppo|huawei|apple|electronics|laptop|harvey norman|courts|senheng|best denki|gadget'),
 ('fashion',r'fashion|apparel|jewel|diamond|watch|wardrobe|boutique|shoes|bag'),
 ('entertainment',r'cinema|movie|gsc|tgv|theme park|concert|ticket|entertainment|attraction|museum|golf'),
 ('automotive',r'car wash|\bauto ?(spa|care|colou?r|lab|service)|tyre|servauto|coating|\bvehicle|\bmotor'),('education',r'education|school|tuition|course|university'),
 ('insurance',r'\binsurance\b|takaful'),('utilities',r'utility|utilities|bill payment|telco|astro|unifi'),
 ('online',r'shopee|lazada|e-?commerce|zalora|taobao|amazon|online (spend|shopping|purchase)'),
 ('shopping',r'shopping|mall|outlet|store|retail|department'),('spend_campaign',r'spend (and|&) win|lucky draw|stand a chance|contest|spend .{0,30}(get|win|earn)')]
def category(s):
    l=s.lower()
    for c,p in CATS:
        if re.search(p,l): return c
    return 'other'
def benefit(title):
    l=title.lower(); d={}
    m=re.search(r'(\d+(?:\.\d+)?)\s?%\s*(off|discount|savings?)',l)
    if m: return {'type':'discount_pct','value_pct':float(m.group(1)),'value_text':m.group(0)}
    m=re.search(r'(\d+(?:\.\d+)?)\s?%\s*(cash\s?back|rebate|cashback)',l)
    if m: return {'type':'cashback_pct','value_pct':float(m.group(1)),'value_text':m.group(0)}
    m=re.search(r'((?:rm|s\$|sgd|\$)\s?[\d,]+(?:\.\d+)?)\s*(off|discount|rebate|cash\s?back|savings?|voucher|e-?voucher|instant rebate)',l)
    if m: return {'type':'amount_'+('voucher' if 'voucher' in m.group(2) else 'off' if m.group(2) in ('off','discount','savings','saving') else 'cashback'),'value_text':m.group(0)}
    if re.search(r'0\s?%',l) and re.search(r'instal|ezypay|easy ?pay|epp|ipp|interest',l): return {'type':'instalment_0pct','value_text':re.search(r'0\s?%[^,.;]{0,40}',l).group(0)}
    if re.search(r'complimentary|free\b|buy \w+,? get|1[- ]for[- ]1|one[- ]for[- ]one',l): return {'type':'freebie','value_text':None}
    if re.search(r'\d+\s?x\s*(points|treats|bonus)|bonus points|miles',l): return {'type':'points_miles','value_text':None}
    if re.search(r'win|lucky draw|stand a chance|contest',l): return {'type':'lucky_draw','value_text':None}
    if re.search(r'cash\s?back|rebate',l): return {'type':'cashback','value_text':None}
    if re.search(r'special (deals?|offers?|price)|privilege|exclusive|deal',l): return {'type':'special_deal','value_text':None}
    return {'type':'other','value_text':None}
def merchant_from_title(t):
    t=t.replace('\u2019',"'")
    for p in [r'@\s*(.+?)(?:\s+(?:with|using|for)\s|\s*[|!:]|$)', r'\bat\s+(?:participating\s+|selected\s+)?(.+?)(?:\s+(?:with|using|when|for|via|in)\s+(?:your\s+)?(?:\w+\s+){0,4}(?:card|cards|credit)|\s*[|!:]|\s+[-–]\s|\s+this\s|\s+from\s|\s+until\s|$)',
              r'\bon\s+(.+?)\s+(?:with|using)\s+(?:your\s+)?(?:\w+\s+){0,4}cards?',
              r'^(.+?)\s*[:|–-]\s+']:
        m=re.search(p,t,re.I)
        if m:
            name=m.group(1).strip(' .,')
            if 3<=len(name)<=70 and not re.search(r'\b(card|cards|credit|bank|maybank|cimb|uob|ocbc|dbs|hsbc|rhb|ambank|promotion|spend|overseas|online|deals?|wheel|settle|privileges?|promotions?|transfer|rates?|fund)\b',name,re.I):
                return name
    return None
NOTCARD=re.compile(r'fixed deposit|home loan|mortgage|personal loan|savings? account|current account|unit trust|remittance|fd\b|hire purchase|car loan|wealth|investment|forex|asb\b|property|account opening',re.I)
TITLE_BAD=re.compile(r'fund\b|reit|transfer|rates?\b|insurexpo|bank differently|ptptn|debit|account|financing|fees and charges|\bfees?\b|referral|winners?|announcement|notice|survey|savings|deposit|loan|investment|insurance plan|\btia\b|remit|forex|e-?statement',re.I)
def is_card_offer(title,text):
    l=text.lower()
    if TITLE_BAD.search(title) and not re.search(r'credit card|card ?member|cardholder',title,re.I): return False,'non_card_title'
    if not re.search(r'card|kad',title,re.I) and l.count('credit card')+l.count('kad kredit')+l.count('cardmember')+l.count('cardholder')<2: return False,'weak_card_evidence'
    if 'credit card' not in l and 'card' not in title.lower() and 'kad kredit' not in l:
        if 'card' not in l: return False,'no_card_mention'
    if NOTCARD.search(title) and 'credit card' not in title.lower(): return False,'non_card_product'
    if 'debit card' in l and 'credit card' not in l and 'credit' not in title.lower(): return False,'debit_only'
    return True,None
def terms_url(links):
    for h,t in links.items():
        if re.search(r'terms|t&c|tnc|t-c|conditions',h+' '+t,re.I) and ('.pdf' in h.lower() or 'tnc' in h.lower() or 'terms' in h.lower()):
            return h
    return None
def min_spend(text):
    m=re.search(r'(?:min(?:imum|\.)?\s*(?:single\s*|accumulated\s*|cumulative\s*|nett\s*)?(?:receipt\s*|retail\s*)?(?:spend(?:ing)?|purchase|transaction|bill)(?:\s*of)?)\s*(?:RM|S\$|SGD)\s?[\d,]+(?:\.\d+)?',text,re.I)
    return ' '.join(m.group(0).split()) if m else None
