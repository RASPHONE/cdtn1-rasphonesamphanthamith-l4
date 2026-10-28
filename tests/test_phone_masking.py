"""QT-15 / NFR4: 100% of phone numbers returned to non-manager roles must
match the exact masked format 3 digits + 4 asterisks + 3 digits."""
import re

from src.services.phone_masking import apply_phone_policy, mask_phone

NFR4_FORMAT = re.compile(r"^\d{3}\*{4}\d{3}$")


def test_mask_ten_digit_phone():
    assert mask_phone("0901234567") == "090****567"


def test_every_masked_ten_digit_phone_matches_nfr4_format():
    phones = [f"09{n:08d}" for n in range(0, 100_000_000, 9_999_991)]

    masked = [mask_phone(phone) for phone in phones]

    assert all(NFR4_FORMAT.match(value) for value in masked)


def test_manager_sees_full_phone():
    ticket = {"ticket_id": 1, "customer_phone": "0901234567"}

    assert apply_phone_policy(ticket, "CENTER_MANAGER")["customer_phone"] == "0901234567"
    assert apply_phone_policy(ticket, "BOARD_OF_DIRECTORS")["customer_phone"] == "0901234567"


def test_other_role_sees_masked_phone_and_original_is_untouched():
    ticket = {"ticket_id": 1, "customer_phone": "0901234567"}

    result = apply_phone_policy(ticket, "TECHNICIAN")

    assert result["customer_phone"] == "090****567"
    assert ticket["customer_phone"] == "0901234567"


def test_too_short_phone_is_fully_hidden():
    assert mask_phone("12345") == "****"
    assert mask_phone(None) is None
