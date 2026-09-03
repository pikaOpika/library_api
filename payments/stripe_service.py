import os
import stripe
from dotenv import load_dotenv

from django.urls import reverse

from borrowings.models import Borrowing
from payments.models import Payment

load_dotenv()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

def create_stripe_session(borrowing: Borrowing, request, amount, payment_type):
    
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
    return Payment.objects.create(
        borrowing=borrowing,
        type=payment_type,
        session_url=session.url,
        session_id=session.id,
        money_to_pay=amount
    )
