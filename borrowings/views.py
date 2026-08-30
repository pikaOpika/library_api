from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet


from borrowings.serializers import BorrowingSerializer, BorrowingDetailSerializer
from borrowings.models import Borrowing


class BorrowingViewSet(
    ListModelMixin, RetrieveModelMixin,
    CreateModelMixin, GenericViewSet
):
    queryset = Borrowing.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        return BorrowingSerializer
