## What changed

<!-- Short summary. List the record IDs you added, changed or removed. -->

Linked issue: #

## Source checklist

- [ ] Every changed record cites an official issuer, network or merchant source URL
- [ ] Offers carry `terms_url` when a deal terms link exists, or `terms_url_null_reason` if it does not
- [ ] No verbatim terms text (`terms_clauses`) is added
- [ ] Dated offers have an `end_date` from the terms or the deal page. Offers with no stated end date are `evergreen` and have `review_by`
- [ ] Sources are official issuer, network or merchant pages
- [ ] `checked_at` is a full date-time with offset on every changed card and offer
- [ ] This PR is linked to an issue
- [ ] `python tools/validate.py` passes locally
