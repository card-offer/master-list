## What changed

<!-- Short summary. List the record IDs you added, changed or removed. -->

Linked issue: #

## Source checklist

- [ ] Every changed record cites an official issuer, network or merchant source URL
- [ ] Offers carry the deal's own T&C link (`terms_url`), or `terms_url_null_reason` if the deal has none
- [ ] Every offer has an `end_date` taken from its T&C or deal page
- [ ] No data comes from aggregator, comparison, deal or review sites
- [ ] `last_checked` is updated on every changed record
- [ ] This PR is linked to an issue
- [ ] `python tools/validate.py` passes locally
