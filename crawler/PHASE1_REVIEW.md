# Phase 1 review follow-up

Reviewed on 2026-11-11 for PR #10. These decisions cover source configuration and the existing Ryt/Paydee evidence. They do not accept the whole census or start phase 2. All robots, rate-limit and public-page rules in `RULES.md` remain in effect. Do not visit sign-in, sign-up or form URLs.

## Registry and source decisions

| issuer | decision | official evidence |
|---|---|---|
| `sg-trust` | Use `trustbank.sg` for the website, allowed domain and card catalogue. Keep coverage `not_covered` until cards and offers are ingested. | https://trustbank.sg/credit-card/ |
| `my-hsbc` | Add `hsbcamanah.com.my` and its card catalogue alongside the existing HSBC hosts. Keep one issuer grouping and mark coverage `partial` because the Amanah catalogue has not been ingested in this review. | https://www.hsbc.com.my/credit-cards/ links to https://www.hsbcamanah.com.my/credit-cards/ |
| `my-aeon-credit` | Keep `myaeoncredit.com.my` as the consumer source. The corporate domain is official, but the regulator's choice of corporate website does not require replacing or broadening the consumer allowlist. | https://aeoncredit.com.my/aeon-credit-introduces-aeon-member-plus-credit-card-the-must-have-card-for-aeon-shoppers/ links to https://myaeoncredit.com.my/ |
| `sg-dbs` | Keep `dbs.com.sg` as the Singapore consumer source. The corporate group host alone does not require a broader allowlist. | https://www.dbs.com/default.page and https://www.dbs.com.sg/personal/cards/cards-comparator.page |

The issuer registries and root index carry updated generation timestamps. MY has 19 issuer records after the proposed ICBC addition; SG has 16. Existing card/offer fetch timestamps and coverage counts are unchanged.

## Verified destinations for phase 1 census checks

The review verified these redirects from the banks' existing official URLs. The following destination hosts are approved for phase 1 census checks only. This is an explicit supplement to the phase 1 source rule, not permission to follow arbitrary cross-host redirects. Check robots on each destination before fetching it. Do not add an issuer or infer a local card product merely because the bank operates a site in another country.

| official starting URL | permitted destination host | reviewed destination URL | country limit |
|---|---|---|---|
| https://www.mbsbbank.com/ | `www.mbsb.com` | https://www.mbsb.com/mbsbbank/ | Malaysia product check. |
| https://www.hdfcbank.com/ | `www.hdfc.bank.in` | https://www.hdfc.bank.in/ | India products do not establish Singapore consumer issuance. Find Singapore-specific evidence. |
| https://www.icicibank.com/ | `www.icici.bank.in` | https://www.icici.bank.in/ | India products do not establish Singapore consumer issuance. Find Singapore-specific evidence. |

If another host is encountered, record the redirect and leave it for review. These permissions do not add the hosts to any issuer's phase 2/3 `official_domains`. Use the country registries for those phases.

## Consumer product scope

- Ryt: keep the identified product outside the credit/charge-card census. The [specific terms](https://www.rytbank.my/specific-terms-and-conditions-20261020) govern the card as a debit card and define Ryt Credit separately as BNPL in section D. The ability to fund a card payment with that facility does not change this catalogue decision.
- Paydee: exclude the identified Visa Corporate Credit Card. [Product terms](https://card.paydee.co/product-terms), section 3, restrict it to business transactions and prohibit personal, household and family use. This decision does not establish the scope of unidentified co-branded programmes.

## Evidence follow-up for Grok Bot

Work on the remaining rows in `ISSUER_CENSUS.md`, and recalculate its totals after each classification change. Preserve the Ryt/Paydee review edits and the registry/source corrections. Refresh the remote branch before committing; preserve concurrent commits and never force-push.

1. Recheck `no_consumer_card` rows supported only by global or foreign-market homepages. UBS currently cites a Malaysia page and says no Singapore page was reached. A missing card link on such a page does not establish a Singapore exclusion. Use country-specific product menus, catalogues, sitemaps or official business-scope statements. If still unresolved, state that in the note and outstanding-work report; do not count it as a confirmed exclusion. Do not invent a new result label without reporting the need for a contract decision.
2. Resolve the Bank of China MY debit-only catalogue versus BNM credit-card-issuer designation; HL Bank SG's Malaysia card link; Citibank N.A. SG's proposed grouping versus the legal issuer of the consumer cards; and Maybank Islamic's proposed grouping under `my-maybank`. A shared website alone is not evidence that a legal entity issues the same consumer cards.
3. Retry unreached entries, prioritising the non-wholesale Singapore entries and Malaysia special checks. Keep the reason and original failed URL when a page remains unavailable. Respect blocks, TLS failures and the three-consecutive-same-failure stop rule.
4. Return country-specific evidence URLs, updated result counts, an explicit list of unresolved decisions, and the private fetch log including robots checks, redirects and the three reported sign-in requests. Do not commit raw logs or evidence, enter credentials, submit forms or start phase 2.

The original census at `b2b6764` has five MY rows explicitly marked `not_reached`: Maybank Islamic in the regulator table, plus Agrobank, MBSB Bank, Diners Club and American Express in the special-check table. The regulator-only MY total of one does not include those four extra checks. It also has 52 SG `not_reached` rows: 43 wholesale and nine outside wholesale. These are review-baseline counts, not a claim that the sites remain unavailable after a retry.

The nine SG non-wholesale retry priorities are BNP Paribas, China Construction Bank, Bangkok Bank, Bank of India, Indian Bank, Indian Overseas Bank, Sumitomo Mitsui Banking Corporation, UCO Bank and Optal Singapore. Recompute this list from the census after retries.

The private fetch log was not available to this review, so crawl compliance and the completeness of the original source sweep have not been independently established. Phase 1 remains under review until the evidence follow-up is assessed.
