import stripe
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from payments.serializers import PaymentSerializer
from payments.models import Payment

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
                Payment.objects.filter(session_id=session_id).update(status=Payment.Status.PAID)
                return Response({"status": payment_status})
            return Response({"status": "payment was unsuccessful"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.StripeError as exc:
            return Response({"status": f"Invalid payment session"}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=["GET"], permission_classes=[AllowAny,])
    def cancel(self, request):
        return Response({"status": "You cancelled payment you can continue later but remember link will expire after 24 hours"})