"""QT-15 / NFR4: customer phone masking.

Center Manager and Board of Directors see the full number; every other role
sees the masked form, e.g. 0901234567 -> 090****567.
"""
from typing import Any, Dict, Iterable, List

ROLES_SEEING_FULL_PHONE = frozenset({"CENTER_MANAGER", "BOARD_OF_DIRECTORS"})

VISIBLE_PREFIX = 3
VISIBLE_SUFFIX = 3
MASK = "****"


def mask_phone(phone: str | None) -> str | None:
    """Keep the first 3 and last 3 digits; replace the middle with 4 asterisks.

    A 10-digit Vietnamese number always becomes exactly 10 characters
    (3 + 4 + 3), which is the format NFR4 measures. Values too short to mask
    meaningfully are fully hidden.
    """
    if phone is None:
        return None
    if len(phone) <= VISIBLE_PREFIX + VISIBLE_SUFFIX:
        return MASK
    return f"{phone[:VISIBLE_PREFIX]}{MASK}{phone[-VISIBLE_SUFFIX:]}"


def can_see_full_phone(role: str | None) -> bool:
    return role in ROLES_SEEING_FULL_PHONE


def apply_phone_policy(ticket: Dict[str, Any], role: str | None) -> Dict[str, Any]:
    """Return a copy of `ticket` with customer_phone masked when required."""
    if can_see_full_phone(role):
        return ticket
    masked = dict(ticket)
    masked["customer_phone"] = mask_phone(masked.get("customer_phone"))
    return masked


def apply_phone_policy_all(tickets: Iterable[Dict[str, Any]], role: str | None) -> List[Dict[str, Any]]:
    return [apply_phone_policy(ticket, role) for ticket in tickets]
