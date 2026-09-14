from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase

from datetime import date, timedelta

from books.models import Book
from borrowings.models import Borrowing


class BorrowingVisibilityTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="a@gmail.com", password="a"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@gmail.com", password="admin"
        )
        self.book = Book.objects.create(
            title="Test",
            author="1",
            cover="SOFT",
            inventory=5,
            daily_fee="10.20",
        )

    def test_books_visible_for_admin(self):
        expected_return_date = date.today() + timedelta(days=7)
        borrowing1 = Borrowing.objects.create(
            expected_return_date=expected_return_date,
            book=self.book,
            user=self.user
        )
        borrowing2 = Borrowing.objects.create(
            expected_return_date=expected_return_date,
            book=self.book,
            user=self.admin
        )
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse("borrowings:borrowing-list"))
        self.assertEqual({item["id"] for item in res.data}, {borrowing1.id, borrowing2.id})
