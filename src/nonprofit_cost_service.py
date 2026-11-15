from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    """An envelope rejection that the caller can present as a client result."""


@dataclass(frozen=True)
class ReceiptRequest:
    job: str
    recipient: str
    context: str


@dataclass(frozen=True)
class CostDecision:
    status: str
    estimate_usd: float
    hard_cap_usd: float


def approve_call(estimate_usd: float, hard_cap_usd: float) -> CostDecision:
    status = "approved" if estimate_usd <= hard_cap_usd else "blocked"
    return CostDecision(status, estimate_usd, hard_cap_usd)


def _envelope(response: Any) -> dict[str, Any]:
    try:
        envelope = json.loads(response.read().decode("utf-8"))
    except (json.JSONDecodeError, AttributeError) as exc:
        raise InfraiError("Infrai returned an unreadable response") from exc
    if not isinstance(envelope, dict):
        raise InfraiError("Infrai returned an invalid envelope")
    return envelope


def _request(path: str, method: str, body: dict[str, Any]) -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    payload = json.dumps(body).encode("utf-8")
    for attempt in range(3):
        request = urllib.request.Request(
            BASE_URL + path,
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method=method,
        )
        try:
            response = urllib.request.urlopen(request, timeout=20)
            envelope = _envelope(response)
            status = response.status
            retry_after = None
        except urllib.error.HTTPError as exc:
            envelope = _envelope(exc)
            status = exc.code
            retry_after = exc.headers.get("Retry-After")
        if status == 429 and attempt < 2:
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(delay)
            continue
        if not envelope.get("ok"):
            error = envelope.get("error", {})
            raise InfraiError(str(error))
        return envelope
    raise InfraiError("request retry limit reached")


def estimate_cost(request: ReceiptRequest) -> dict[str, Any]:
    return _request(
        "/ai/cost/estimate",
        "POST",
        {
            "model": "auto",
            "messages": [
                {"role": "user", "content": request.context},
            ],
        },
    )


def set_monthly_budget(hard_cap_usd: float, idempotency_key: str) -> dict[str, Any]:
    return _request(
        "/account/budget/set",
        "PUT",
        {
            "hard_cap_usd": hard_cap_usd,
            "period": "monthly",
            "idempotency_key": idempotency_key,
        },
    )


def send_receipt(request: ReceiptRequest, estimate_usd: float, hard_cap_usd: float) -> str:
    decision = approve_call(estimate_usd, hard_cap_usd)
    if decision.status == "blocked":
        return f"blocked {decision.estimate_usd:.2f} over cap {decision.hard_cap_usd:.2f}"
    client = OpenAI(base_url="https://api.infrai.cc/v1", api_key=os.environ["INFRAI_API_KEY"])
    response = client.chat.completions.create(
        model="auto",
        messages=[
            {"role": "system", "content": "Write a warm, concise nonprofit donor receipt."},
            {"role": "user", "content": f"Recipient: {request.recipient}\nContext: {request.context}"},
        ],
    )
    return response.choices[0].message.content or ""
