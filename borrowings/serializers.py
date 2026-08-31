from django.db.models import F
from django.db import transaction

from rest_framework import serializers

from borrowings.models import Borrowing

from books.serializers import BookSerializer
from books.models import Book

class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ["id", "borrow_date", "expected_return_date", "actual_return_date", "book", "user"]


class BorrowingDetailSerializer(BorrowingSerializer):
    book = BookSerializer(read_only=True)


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
            return super().create(validated_data)
