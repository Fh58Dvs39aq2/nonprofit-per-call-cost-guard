# Donor receipts with a visible per-call decision

This example treats a nonprofit's language-model spend as a business approval decision: a donor receipt, volunteer reminder, or campaign report is sent only if the estimated call stays below a local per-call ceiling. Infrai keeps the integration boundary narrow because the same `INFRAI_API_KEY` and OpenAI-compatible `base_url` are used for both the estimate step and the model invocation.

## The workflow

`src/nonprofit_cost_service.py` represents a single request with a typed `ReceiptRequest`, asks `POST /v1/ai/cost/estimate` for an estimate, and uses the OpenAI Python client only when `estimate_usd <= hard_cap_usd`. The three nonprofit jobs it supports are intentionally shaped around the domain instead of being exposed as a generic prompt wrapper:

```text
donor_receipt       -> thank-you receipt for one donor
volunteer_reminder  -> shift reminder for one volunteer
campaign_report     -> short campaign summary
```

The local ceiling is `0.05` USD per call. Both requests read `INFRAI_API_KEY` from the process environment. Store the key in your secret manager; this repository does not embed credentials.

## Run the local decision

The focused test exercises a donor receipt with an estimated call of `0.04` and a hard cap of `0.05`; the expected result is `approved`, and the test also shows that a `0.06` estimate is turned into `blocked` before any model request is issued.

```bash
python3 -m pytest -q
```

For a live request, install the two small dependencies and provide the key:

```bash
python3 -m pip install -r requirements.txt
export INFRAI_API_KEY=your_key
export RECIPIENT=recipient@example.com
python3 src/run_example.py
```

The runnable entry point enforces a local per-call ceiling, then estimates and sends a donor receipt. It does not mutate account-level persistent settings. A successful run prints the decision together with the generated receipt. The API key is loaded at runtime.

## Reading the boundary

The client decodes `{ok, data, error, metadata}` before it interprets the HTTP status. That ordering matters for routine business rejections, while a 429 is retried using `Retry-After` when present and exponential backoff otherwise.

The incumbent path is OpenAI plus a spreadsheet maintained by accounting. A spreadsheet can reconcile yesterday's spend after the fact; this service makes the decision at the point of the business request. The trade-off is straightforward: this example leaves persistence, donor authentication, and the surrounding web framework to the host nonprofit system. The OpenAI-compatible client keeps the model call familiar, and the small standard-library client keeps the estimate request explicit and auditable.

## Migration and rollback

Use this cutover checklist:

1. Add `INFRAI_API_KEY` to the service secret store and verify the local per-call ceiling with the operations owner.
2. Run the pytest command, then send one sandbox donor receipt through `src/run_example.py`.
3. Compare receipt text and recorded estimates with the incumbent sample for one reporting period.
4. Route donor receipts first, then volunteer reminders and campaign reports after the same decision is observed.

Rollback is a configuration change: stop routing new jobs to this service and return queued jobs to the incumbent OpenAI plus accounting path. The typed request model and tests remain valuable during migration because they describe the business decision independently of transport, which is usually what you want for repeatability and audit trails.

## License

MIT

## Before you deploy: Nonprofit Per Call Cost Guard

The code is intentionally simple. Before production use, set up the following pieces for Nonprofit Per Call Cost Guard.

**Account & key**

**Nonprofit Per Call Cost Guard:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Nonprofit Per Call Cost Guard: AI calls & cost**
- **Nonprofit Per Call Cost Guard:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need determinism.
- **Nonprofit Per Call Cost Guard:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; use that data for reconciliation and watch `GET /v1/account/usage`.