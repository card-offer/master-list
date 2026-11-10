import sys,json; sys.path.insert(0,'pipeline/sources'); import ws
from seedlist import S
probe={r['url']:r for r in json.load(open('raw/sources/probe.json'))}
DROP={ # wrong guesses superseded by the real page found on the official site
 'https://www.cimb.com.my/en/personal/promotions/cards-promotions.html','https://www.cimb.com.my/en/personal/campaigns/cimb-deals.html',
 'https://www.rhbgroup.com/personal/promotions/index.html','https://www.rhbgroup.com/personal/promotions/cards/index.html','https://www.rhbgroup.com/rhbrewards/index.html',
 'https://www.ambank.com.my/promotions/cards','https://www.uob.com.my/personal/promotions/cards/index.page',
 'https://www.ocbc.com.my/personal-banking/promotions','https://www.ocbc.com.my/personal-banking/cards/promotions','https://www.ocbc.com.my/personal-banking/cards/card-promotions',
 'https://www.hsbc.com.my/credit-cards/offers/','https://www.hsbc.com.my/credit-cards/home-and-away/','https://www.sc.com/my/credit-cards/the-good-life/','https://www.sc.com/sg/promotions/the-good-life/',
 'https://www.alliancebank.com.my/promotions/cards','https://www.affinalways.com/en/card-promotions','https://www.bsn.com.my/Promotion','https://www.bsn.com.my/',
 'https://www.alrajhibank.com.my/promotions/','https://www.americanexpress.com/en-my/benefits/offers/','https://www.americanexpress.com/en-sg/benefits/offers/','https://www.americanexpress.com/en-sg/campaigns/','https://www.americanexpress.com/en-sg/network/offers/',
 'https://www.visa.com.my/en_MY/visa-offers-and-perks/','https://www.visa.com.sg/en_SG/visa-offers-and-perks/','https://www.unionpayintl.com/en/servicesProducts/offers/',
 'https://www.specials.jcb/en/my/','https://www.specials.jcb/en/sg/','https://www.dbs.com.sg/personal/promotion/default.page','https://www.dbs.com.sg/personal/deals/default.page','https://www.posb.com.sg/personal/deals/default.page',
 'https://www.ocbc.com/personal-banking/cards/promotions','https://www.ocbc.com/personal-banking/deals','https://www.ocbc.com/personal-banking/cards/card-promotion.page',
 'https://www.uob.com.sg/personal/promotions/cards/index.page','https://www.uob.com.sg/personal/promotions/dining/index.page','https://www.citibank.com.sg/credit-cards/promotions/','https://www.citibank.com.sg/gcb/credit_cards/citiworld-privileges.htm',
 'https://www.hsbc.com.sg/credit-cards/offers/','https://www.hsbc.com.sg/entertainer/','https://www.maybank2u.com.sg/en/personal/promotions/index.page','https://www.maybank2u.com.sg/en/personal/promotions/cards/index.page',
 'https://www.bankofchina.com/sg/pbservice/pb4/','https://www.maribank.sg/credit-card','https://www.dcs.sg/','https://www.rhbgroup.com.sg/rhb/personal/cards','https://www.mastercard.com/sg/en/personal/offers-and-promotions.html',
 'https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/promotions/index.page','https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/promotions/cards/treats.page','https://www.global.jcb/en/','https://www.gxs.com.sg/','https://www.bankrakyat.com.my/'}
EXTRA=[
('MY','RHB','https://www.rhbgroup.com/cards/promotions-privileges/index.html','merchant_offers'),
('MY','RHB','https://www.rhbgroup.com/cards/mastercard-offers/index.html','merchant_offers'),
('MY','RHB','https://www.rhbgroup.com/ApplyandSpendCard/index.html','promotions'),
('MY','RHB','https://www.rhbgroup.com/btcx/index.html','promotions'),
('MY','OCBC','https://www.ocbc.com.my/personal-banking/promotion','promotions'),
('MY','Affin','https://www.affinalways.com/en/promotions?group=Personal&product_filter=Cards','promotions'),
('MY','Affin','https://www.affinalways.com/flights','promotions'),
('MY','BSN','https://www.bsn.com.my/page/Shopee1111','promotions'),
('MY','BSN','https://www.bsn.com.my/cms/upload/pdf/promotion/2026/zus_coffee_apr_tnc_eng.pdf','tnc'),
('MY','Bank Rakyat','https://www.bankrakyat.com.my/assets/documents/PDS%20CREDIT%20CARD-i%20(BM%202026).pdf','tnc'),
('MY','Kuwait Finance House','https://www.kfh.com.my/en/home/Personal/Cards/credit-cards.html','issuer_check'),
('MY','Bank Islam','https://www.bankislam.com/personal-banking/bank-islam-cards/bank-islam-credit-card-i/','catalogue'),
('MY','Visa','https://www.visa.com.my/en_my/visa-offers-and-perks/','network_portal'),
('MY','JCB','https://www.specialoffers.jcb/en/campaign/d/southeast-and-south-asia/malaysia/','network_portal'),
('SG','Visa','https://www.visa.com.sg/en_sg/visa-offers-and-perks/','network_portal'),
('SG','JCB','https://www.specialoffers.jcb/en/campaign/d/southeast-and-south-asia/singapore/','network_portal'),
('SG','OCBC','https://www.ocbc.com/personal-banking/cards/card-promotion','merchant_offers'),
('SG','American Express','https://www.americanexpress.com/en-sg/benefits/the-platinum-card/dining/','merchant_offers'),
('SG','American Express','https://www.americanexpress.com/en-sg/benefits/the-platinum-card/dining/love-dining-experience/','merchant_offers'),
('SG','American Express','https://www.americanexpress.com/en-sg/campaigns/the-platinum-card/','promotions'),
('SG','Maybank','https://www.maybank2u.com.sg/en/promotions/cards/index.page','promotions'),
('SG','Maybank','https://cardspromo.maybank2u.com.sg/','merchant_offers'),
('SG','Maybank','https://www.maybank2u.com.sg/iwov-resources/sg/pdf/cards/applynow-tnc.pdf','tnc'),
('SG','BOC','https://www.bankofchina.com/sg/bcservice/','catalogue'),
('SG','MariBank','https://www.maribank.sg/product/mari-credit-card','catalogue'),
('SG','ICBC','https://www.icbc.com.sg/en/column/1438059017535897814.html','catalogue'),
('SG','DCS Card Centre','https://cards.dcscc.com/','catalogue'),
('SG','DCS Card Centre','https://dcscc.com/campaigns','promotions'),
('SG','DCS Card Centre','https://cards.dcscc.com/dconvertoffer','promotions'),
('SG','DCS Card Centre','https://cards.dcscc.com/ultimate','promotions'),
]
rows=[]
for cc,b,u,pt in S+EXTRA:
    if u in DROP: continue
    p=probe.get(u); note=''; st='to do'
    if p:
        if p['status']==0: st='blocked'; note='timeout / no response from this network (curl)'
        elif p['status']==403: st='blocked'; note='HTTP 403 (bot protection)'
        elif p['status'] in (404,406): st='blocked'; note=f"HTTP {p['status']}"
        elif p['words']<5: st='to do'; note='JS-only shell (needs headless)'
        if pt=='issuer_check': note=(note+'; ' if note else '')+'check whether issuer offers credit cards'
    rows.append(dict(country=cc,bank=b,source_url=u,page_type=pt,status=st,cards_found='',offers_found='',date_checked='',last_verified='',notes_blockers=note))
ws.save(rows); print(len(rows))
