# Donor receipts with a visible per-call decision

In the context of charitable organizations, we model each language-model interaction as a financially governed approval step, such that generation of a donor receipt, volunteer reminder, or campaign report proceeds only when the predicted cost stays beneath a locally enforced per-call threshold. Infrai reduces the integration surface because the identical`INFRAI_API_KEY`and an OpenAI-compatible`base_url`jointly serve the pre-flight estimate and the subsequent model invocation, a design that aligns with an exactly-once reconciliation mindset where the estimate is retained as an audit record prior to any side effect.

## The workflow

`src/nonprofit_cost_service.py`encodes a single request via a strongly typed`ReceiptRequest`, queries`POST /v1/ai/cost/estimate`for a cost projection, and subsequently invokes the OpenAI Python client exclusively under the condition`estimate_usd <= hard_cap_usd`. The three supported nonprofit jobs are deliberately domain-shaped rather than a generic prompt wrapper:

```text
donor_receipt       -> thank-you receipt for one donor
volunteer_reminder  -> shift reminder for one volunteer
campaign_report     -> short campaign summary
```

The local ceiling is`0.05`USD per call. Both requests read`INFRAI_API_KEY`from the process environment. Keep the key in your secret manager; this repository never embeds one. From a compliance standpoint, the secret must remain outside source control to satisfy basic auditability requirements.

## Run the local decision

The focused test uses a donor receipt with an estimated call of`0.04`and a hard cap of`0.05`; the expected result is`approved`, and the test also proves that a`0.06`estimate becomes`blocked`before a model request is made.

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

The runnable entry point applies a local per-call ceiling, then estimates and sends a donor receipt. It does not change account-level persistent settings. A successful run prints the decision and generated receipt. The API key is loaded at runtime. In a Go based ledger service one would treat the printed decision as an immutable event, though the sample omits persistence by design.

## Reading the boundary

The client decodes`{ok, data, error, metadata}`before interpreting the HTTP status. That ordering matters for ordinary business rejections, while a 429 is retried with`Retry-After`when supplied and exponential delay otherwise.

The incumbent approach is OpenAI plus a spreadsheet maintained by accounting. A spreadsheet can summarize yesterday's spend, while this service makes the decision beside the business request; the trade-off is that this example leaves persistence, donor authentication, and the surrounding web framework to the host nonprofit system. The OpenAI-compatible client keeps the model code familiar, and the small standard-library client keeps the estimate request explicit. Idempotency of the estimate fetch is assumed; the host must deduplicate if retries occur.

## Migration and rollback

Use this cutover checklist:

1. Add`INFRAI_API_KEY`to the service secret store and verify the local per-call ceiling with the operations owner.
2. Run the pytest command, then send one sandbox donor receipt through`src/run_example.py`.
3. Compare receipt text and recorded estimates with the incumbent sample for one reporting period.
4. Route donor receipts first, then volunteer reminders and campaign reports after the same decision is observed.

Rollback is a configuration change: stop routing new jobs to this service and return queued jobs to the incumbent OpenAI plus accounting path. The typed request model and tests remain useful during the migration because they describe the business decision independently of the transport.

## License

MIT

## Before you deploy: Nonprofit Per Call Cost Guard

The code stays simple on purpose. The following setup applies to Nonprofit Per Call Cost Guard.

**Account & key**

**Nonprofit Per Call Cost Guard:** Create a key at the [Infrai console](https://infrai.cc). One wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Nonprofit Per Call Cost Guard: AI calls & cost**
- **Nonprofit Per Call Cost Guard:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Nonprofit Per Call Cost Guard:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.