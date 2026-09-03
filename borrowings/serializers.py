from django.db.models import F
from django.db import transaction

from rest_framework import serializers

from borrowings.models import Borrowing
from books.serializers import BookSerializer
from books.models import Book

from notifications.telegram import send_telegram_message
from payments.stripe_service import create_stripe_session
from payments.serializers import PaymentSerializer
from payments.models import Payment

class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ["id", "borrow_date", "expected_return_date", "actual_return_date", "book", "user", "payments"]


class BorrowingDetailSerializer(BorrowingSerializer):
    book = BookSerializer(read_only=True)
    payments = PaymentSerializer(read_only=True, many=True)


class BorrowingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ["expected_return_date", "book"]

    def validate_book(self, value):
        if value.inventory == 0:
            raise serializers.ValidationError("This book is out of stock")
        return value

    def create(self, validated_data):
        book = validated_data.get("book")
        with transaction.atomic():
            Book.objects.filter(pk=book.id).update(inventory=F("inventory") - 1)
            borrowing = super().create(validated_data)
        count_days = (borrowing.expected_return_date - borrowing.borrow_date).days
        amount = count_days * borrowing.book.daily_fee if count_days else borrowing.book.daily_fee
        create_stripe_session(
            borrowing=borrowing,
            request=self.context["request"],
            amount=amount,
            payment_type=Payment.Type.PAYMENT
        )
        send_telegram_message(
            f"User {validated_data['user']} borrowed book {book.title} expected return date {validated_data.get('expected_return_date')}"
        )
        return borrowing

