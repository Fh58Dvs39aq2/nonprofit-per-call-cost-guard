import os

from nonprofit_cost_service import (
    ReceiptRequest,
    approve_call,
    estimate_cost,
    send_receipt,
)


def main() -> None:
    request = ReceiptRequest(
        job="donor_receipt",
        recipient=os.environ["RECIPIENT"],
        context="Thank the donor for a spring food-bank donation and mention the next volunteer day.",
    )
    hard_cap_usd = 0.05
    estimate = estimate_cost(request)
    estimate_usd = float(estimate["data"]["breakdown"]["final"])
    decision = approve_call(estimate_usd, hard_cap_usd)
    print({"decision": decision.status, "estimate_usd": estimate_usd})
    if decision.status == "approved":
        print(send_receipt(request, estimate_usd, hard_cap_usd))


if __name__ == "__main__":
    main()
