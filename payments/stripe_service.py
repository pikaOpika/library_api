import stripe

from django.urls import reverse
from django.conf import settings

from borrowings.models import Borrowing
from payments.models import Payment


stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_session(session_id):
    return stripe.checkout.Session.retrieve(session_id)


def build_stripe_session(borrowing: Borrowing, request, amount):
    success_path = reverse("payments:payment-success")
    cancel_path = reverse("payments:payment-cancel")
    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": borrowing.book.title},
                    "unit_amount": int(amount * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=request.build_absolute_uri(success_path) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(cancel_path),
    )
    return session


def create_stripe_session(borrowing: Borrowing, request, amount, payment_type):
    session = build_stripe_session(borrowing, request, amount)
    return Payment.objects.create(
        borrowing=borrowing,
        type=payment_type,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=amount
    )



def update_stripe_session(payment, request):
    session = build_stripe_session(payment.borrowing, request, payment.money_to_pay)
    payment.session_id = session.id
    payment.session_url = session.url
    payment.status = Payment.Status.PENDING
    payment.save(update_fields=["session_id", "session_url", "status"])
    return payment
