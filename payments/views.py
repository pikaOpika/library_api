import stripe
import logging
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from payments.stripe_service import get_stripe_session, update_stripe_session
from payments.serializers import PaymentSerializer
from payments.models import Payment

from notifications.telegram import send_telegram_message


from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

logger = logging.getLogger(__name__)


class PaymentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = self.queryset.all()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(borrowing__user=self.request.user)

    @extend_schema(
        summary="Stripe success redirect",
        description=(
            "Stripe redirects the browser here after payment. "
            "The session is verified with Stripe before the payment "
            "is marked as paid."
        ),
        parameters=[
            OpenApiParameter(
                name="session_id",
                type=OpenApiTypes.STR,
                required=True,
                description="Stripe checkout session id",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[
            AllowAny,
        ],
    )
    def success(self, request):
        session_id = request.query_params.get("session_id")
        try:
            session = get_stripe_session(session_id)
            payment_status = session.payment_status
            if payment_status == "paid":
                payment = Payment.objects.get(session_id=session_id)
                if payment.status == Payment.Status.PAID:
                    return Response({"detail": "You already paid"})
                payment.status = Payment.Status.PAID
                payment.save()
                send_telegram_message(
                    f"Payment received: ${payment.money_to_pay} from "
                    f"{payment.borrowing.user.email} for "
                    f'"{payment.borrowing.book.title}" ({payment.type})'
                )
                return Response({"status": payment_status})
            return Response(
                {"status": "payment was unsuccessful"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.StripeError as exc:
            logger.error("Stripe got an error %s", exc)
            return Response(
                {"status": "Invalid payment session"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Couldn't find your payment with this session_id"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        summary="Stripe cancel redirect",
        description=(
            "Stripe redirects the browser here when the user leaves the "
            "checkout page without paying. Nothing is changed: the payment "
            "stays unpaid and its link remains valid for 24 hours."
        ),
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(
        detail=False,
        methods=["GET"],
        permission_classes=[
            AllowAny,
        ],
    )
    def cancel(self, request):
        return Response(
            {
                "status": "You cancelled payment you can continue later "
                "but remember link will expire after 24 hours"
            }
        )

    @extend_schema(
        summary="Stripe renews payments",
        description=(
            "Creates a new Stripe checkout session for a payment whose "
            "previous session has expired, and returns the new link. "
            "The payment goes back to PENDING. "
            "Payments in any other status are rejected with 400."
        ),
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["POST"])
    def renew(self, request, pk):
        payment = self.get_object()
        if payment.status != Payment.Status.EXPIRED:
            return Response(
                {"detail": "Only expired payments can be renewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment = update_stripe_session(payment, request)
        return Response(
            {
                "detail": "Payment renewed.",
                "session_url": payment.session_url,
            }
        )
