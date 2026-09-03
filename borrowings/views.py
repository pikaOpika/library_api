from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from django.db.models import F
from django.db import transaction
from django.conf import settings

from datetime import date

from borrowings.serializers import (
    BorrowingSerializer, BorrowingDetailSerializer,
    BorrowingCreateSerializer
)
from borrowings.models import Borrowing

from books.models import Book

from payments.stripe_service import create_stripe_session
from payments.models import Payment

class BorrowingViewSet(
    ListModelMixin, RetrieveModelMixin,
    CreateModelMixin, GenericViewSet
):
    queryset = Borrowing.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BorrowingDetailSerializer
        if self.action == "create":
            return BorrowingCreateSerializer
        return BorrowingSerializer

    def get_queryset(self):
        queryset = self.queryset.all()
        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")

        if user_id and self.request.user.is_staff:
            if not user_id.isdigit():
                raise ValidationError("user_id must be a number")
            queryset = queryset.filter(user=int(user_id))

        if is_active == "true":
            queryset = queryset.filter(actual_return_date__isnull=True)

        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    @action(methods=["POST"], detail=True, url_path="return")
    def borrowing_return(self, request, pk):
        borrowing = self.get_object()
        if borrowing.actual_return_date is not None:
            return Response(
                {"detail": "You already returned book"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            Borrowing.objects.filter(pk=borrowing.pk).update(
                actual_return_date = date.today(),
            )
            Book.objects.filter(pk=borrowing.book.id).update(
                inventory=F("inventory") + 1
            )

        if date.today() > borrowing.expected_return_date:
            days = (date.today() - borrowing.expected_return_date).days
            money_to_pay = days * borrowing.book.daily_fee * settings.FINE_MULTIPLIER
            create_stripe_session(
                borrowing=borrowing,
                request=self.request,
                amount=money_to_pay,
                payment_type=Payment.Type.FINE
            )
        return Response({"detail": "You returned book"})

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
