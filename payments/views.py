from rest_framework import viewsets
from rest_framework import mixins

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

