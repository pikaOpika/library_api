import stripe
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from payments.serializers import PaymentSerializer
from payments.models import Payment

from notifications.telegram import send_telegram_message

class PaymentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer


    def get_queryset(self):
        queryset = self.queryset.all()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(borrowing__user=self.request.user)

    @action(detail=False, methods=["GET"], permission_classes=[AllowAny,])
    def success(self, request):
        session_id = request.query_params.get("session_id")
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            payment_status = session.payment_status
            if payment_status == "paid":
                payment = Payment.objects.get(session_id=session_id)
                payment.status = Payment.Status.PAID
                payment.save()
                send_telegram_message(
                    f'Payment received: ${payment.money_to_pay} from {payment.borrowing.user.email} for "{payment.borrowing.book.title}" ({payment.type})'
                )
                return Response({"status": payment_status})
            return Response({"status": "payment was unsuccessful"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.StripeError as exc:
            return Response({"status": "Invalid payment session"}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=["GET"], permission_classes=[AllowAny,])
    def cancel(self, request):
        return Response({"status": "You cancelled payment you can continue later but remember link will expire after 24 hours"})
