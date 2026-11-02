"""
Payment service — provider-independent payment processing.

IMPORTANT: PAYMENT_PROVIDER=simulator is for development only.
Never use the simulator in production. Configure razorpay or stripe with real credentials.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class PaymentProvider(ABC):
    @abstractmethod
    async def create_checkout_session(self, amount_minor: int, currency: str, description: str, metadata: dict) -> dict:
        ...

    @abstractmethod
    async def verify_payment(self, payment_id: str, signature: str | None = None) -> bool:
        ...

    @abstractmethod
    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class SimulatorPaymentProvider(PaymentProvider):
    """
    DEVELOPMENT ONLY payment simulator.
    Clearly labeled — never use in production.
    All 'payments' succeed immediately. No real money moves.
    """
    provider_name = "simulator"

    async def create_checkout_session(self, amount_minor: int, currency: str, description: str, metadata: dict) -> dict:
        session_id = f"sim_{uuid.uuid4().hex[:16]}"
        logger.warning(
            "DEVELOPMENT PAYMENT SIMULATOR — no real payment processed",
            session_id=session_id,
            amount_minor=amount_minor,
            currency=currency,
        )
        return {
            "session_id": session_id,
            "checkout_url": f"/billing/simulate-checkout?session={session_id}&amount={amount_minor}",
            "provider": "simulator",
            "amount_minor": amount_minor,
            "currency": currency,
            "_warning": "DEVELOPMENT ONLY — no real payment",
        }

    async def verify_payment(self, payment_id: str, signature: str | None = None) -> bool:
        if not payment_id.startswith("sim_"):
            return False
        logger.warning("DEVELOPMENT SIMULATOR: payment verified", payment_id=payment_id)
        return True

    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        logger.warning("DEVELOPMENT SIMULATOR: webhook received")
        return {"event": "payment.success", "simulated": True}


class RazorpayPaymentProvider(PaymentProvider):
    provider_name = "razorpay"

    def __init__(self):
        self._client = None

    def _get_client(self):
        if not self._client:
            import razorpay  # type: ignore
            self._client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        return self._client

    async def create_checkout_session(self, amount_minor: int, currency: str, description: str, metadata: dict) -> dict:
        import asyncio
        client = self._get_client()
        order = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.order.create({
                "amount": amount_minor,
                "currency": currency,
                "receipt": str(uuid.uuid4()),
                "notes": metadata,
            })
        )
        return {"session_id": order["id"], "provider": "razorpay", "order": order}

    async def verify_payment(self, payment_id: str, signature: str | None = None) -> bool:
        import hmac
        import hashlib
        if not signature:
            return False
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            payment_id.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        import json
        import hmac
        import hashlib
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid webhook signature")
        return json.loads(payload)


class StripePaymentProvider(PaymentProvider):
    provider_name = "stripe"

    async def create_checkout_session(self, amount_minor: int, currency: str, description: str, metadata: dict) -> dict:
        import stripe  # type: ignore
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = await stripe.checkout.Session.create_async(
            payment_method_types=["card"],
            line_items=[{"price_data": {"currency": currency, "unit_amount": amount_minor, "product_data": {"name": description}}, "quantity": 1}],
            mode="payment",
            success_url=f"{settings.APP_URL}/billing/success",
            cancel_url=f"{settings.APP_URL}/billing/cancel",
            metadata=metadata,
        )
        return {"session_id": session.id, "checkout_url": session.url, "provider": "stripe"}

    async def verify_payment(self, payment_id: str, signature: str | None = None) -> bool:
        import stripe  # type: ignore
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            pi = await stripe.PaymentIntent.retrieve_async(payment_id)
            return pi.status == "succeeded"
        except Exception:
            return False

    async def handle_webhook(self, payload: bytes, signature: str) -> dict:
        import stripe  # type: ignore
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
            return dict(event)
        except stripe.error.SignatureVerificationError as e:
            raise ValueError(f"Invalid Stripe webhook signature: {e}")


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "simulator":
        if settings.is_production:
            raise RuntimeError("Payment simulator cannot be used in production. Configure a real payment provider.")
        return SimulatorPaymentProvider()
    elif settings.PAYMENT_PROVIDER == "razorpay":
        if not settings.RAZORPAY_KEY_ID:
            raise RuntimeError("RAZORPAY_KEY_ID not configured")
        return RazorpayPaymentProvider()
    elif settings.PAYMENT_PROVIDER == "stripe":
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY not configured")
        return StripePaymentProvider()
    else:
        raise RuntimeError(f"Unknown payment provider: {settings.PAYMENT_PROVIDER}")
