import stripe
import logging
from celery import shared_task

from payments.stripe_service import get_stripe_session

from payments.models import Payment

logger = logging.getLogger(__name__)


@shared_task
def check_expired_payments():
    for payment in Payment.objects.filter(status=Payment.Status.PENDING):
        try:
            session = get_stripe_session(payment.session_id)
        except stripe.StripeError as exc:
            logger.error("Stripe error for payment %s: %s", payment.id, exc)
            continue
        if session.status == "expired":
            payment.status = Payment.Status.EXPIRED
            payment.save(update_fields=["status"])

