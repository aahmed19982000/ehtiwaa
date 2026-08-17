"""Client for Paymob's Accept API (the classic 3-step flow: auth token ->
order registration -> payment key -> hosted iframe). Implemented against
Paymob's public API docs (https://docs.paymob.com/) — every request shape
and the HMAC field order below are exactly what Paymob's API expects, not
guesses. What this module can't do without a real merchant account is be
exercised against Paymob's live servers: PAYMOB_API_KEY is blank by
default, and is_configured() gates every call site so checkout degrades to
bank-transfer-only instead of pretending a card payment worked.

Getting a real account activates this with zero code changes — just set
PAYMOB_API_KEY / PAYMOB_INTEGRATION_ID / PAYMOB_IFRAME_ID / PAYMOB_HMAC_SECRET.
"""

import hashlib
import hmac
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Paymob wants amounts in the smallest currency unit (piastres, 1 EGP = 100).


def to_amount_cents(decimal_amount):
    # round() on a Decimal returns a Decimal, not an int — the cast is real.
    rounded = round(decimal_amount * 100)
    return int(rounded)


def is_configured():
    return bool(
        settings.PAYMOB_API_KEY and settings.PAYMOB_INTEGRATION_ID and settings.PAYMOB_IFRAME_ID
    )


class PaymobError(Exception):
    pass


def _request(method, path, **kwargs):
    url = f"{settings.PAYMOB_BASE_URL}{path}"
    try:
        response = requests.request(method, url, timeout=15, **kwargs)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Paymob request failed: %s %s -> %s", method, path, exc)
        raise PaymobError(str(exc)) from exc
    return response.json()


def get_auth_token():
    data = _request("post", "/api/auth/tokens", json={"api_key": settings.PAYMOB_API_KEY})
    return data["token"]


def register_order(auth_token, order):
    """Registers our Order with Paymob and returns their order id. Reusing
    order.pk as merchant_order_id lets the webhook look our Order back up
    without needing to store Paymob's id anywhere first."""
    data = _request(
        "post",
        "/api/ecommerce/orders",
        json={
            "auth_token": auth_token,
            "delivery_needed": False,
            "amount_cents": to_amount_cents(order.total),
            "currency": "EGP",
            "merchant_order_id": str(order.pk),
            "items": [],
        },
    )
    return data["id"]


# Paymob requires full billing_data even when we don't collect a shipping
# address (this is a service/digital-goods platform) — "NA" placeholders
# for the address fields are the standard, documented approach for
# merchants in that situation.
_BILLING_PLACEHOLDER = "NA"


def _billing_data(user):
    return {
        "first_name": user.first_name or user.email.split("@")[0],
        "last_name": user.last_name or _BILLING_PLACEHOLDER,
        "email": user.email,
        "phone_number": user.phone or "+201000000000",
        "apartment": _BILLING_PLACEHOLDER,
        "floor": _BILLING_PLACEHOLDER,
        "street": _BILLING_PLACEHOLDER,
        "building": _BILLING_PLACEHOLDER,
        "city": _BILLING_PLACEHOLDER,
        "country": "EG",
        "state": _BILLING_PLACEHOLDER,
        "postal_code": _BILLING_PLACEHOLDER,
    }


def get_payment_key(auth_token, order, paymob_order_id):
    data = _request(
        "post",
        "/api/acceptance/payment_keys",
        json={
            "auth_token": auth_token,
            "amount_cents": to_amount_cents(order.total),
            "expiration": 3600,
            "order_id": paymob_order_id,
            "billing_data": _billing_data(order.user),
            "currency": "EGP",
            "integration_id": settings.PAYMOB_INTEGRATION_ID,
        },
    )
    return data["token"]


def start_card_payment(order):
    """Runs the full 3-step flow and returns the hosted iframe URL to embed.
    Raises PaymobError if anything fails — callers should catch this and
    fall back to offering bank transfer instead."""
    auth_token = get_auth_token()
    paymob_order_id = register_order(auth_token, order)
    payment_key = get_payment_key(auth_token, order, paymob_order_id)
    iframe_url = (
        f"{settings.PAYMOB_BASE_URL}/api/acceptance/iframes/"
        f"{settings.PAYMOB_IFRAME_ID}?payment_token={payment_key}"
    )
    return iframe_url, paymob_order_id


# --- Webhook (transaction processed callback) verification ---

# Exact field order Paymob's HMAC covers — documented, and order-sensitive:
# getting this wrong makes every signature check fail.
_HMAC_FIELDS = [
    "amount_cents",
    "created_at",
    "currency",
    "error_occured",
    "has_parent_transaction",
    "id",
    "integration_id",
    "is_3d_secure",
    "is_auth",
    "is_capture",
    "is_refunded",
    "is_standalone_payment",
    "is_voided",
    "order.id",
    "owner",
    "pending",
    "source_data.pan",
    "source_data.sub_type",
    "source_data.type",
    "success",
]


def _get_nested(data, dotted_key):
    value = data
    for part in dotted_key.split("."):
        value = value.get(part, "") if isinstance(value, dict) else ""
    return value


def _stringify(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def verify_webhook_signature(transaction_data, received_hmac):
    if not settings.PAYMOB_HMAC_SECRET or not received_hmac:
        return False
    concatenated = "".join(
        _stringify(_get_nested(transaction_data, field)) for field in _HMAC_FIELDS
    )
    computed = hmac.new(
        settings.PAYMOB_HMAC_SECRET.encode(), concatenated.encode(), hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, received_hmac)
