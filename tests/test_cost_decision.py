from src.nonprofit_cost_service import ReceiptRequest, approve_call


def test_donor_receipt_is_approved_at_the_ceiling_and_blocked_above_it():
    request = ReceiptRequest("donor_receipt", "Maya Chen", "spring food-bank donation")
    assert request.job == "donor_receipt"
    assert approve_call(0.05, 0.05).status == "approved"
    assert approve_call(0.06, 0.05).status == "blocked"
