from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase

from datetime import date, timedelta

from books.models import Book
from borrowings.models import Borrowing


class BorrowingSetUp(APITestCase):
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
        self.expected_return_date = date.today() + timedelta(days=7)
        self.borrowing1 = Borrowing.objects.create(
            expected_return_date=self.expected_return_date,
            book=self.book,
            user=self.user
        )
        self.borrowing2 = Borrowing.objects.create(
            expected_return_date=self.expected_return_date,
            book=self.book,
            user=self.admin
        )


class BorrowingVisibilityTests(BorrowingSetUp):
    def test_admin_sees_all_borrowings(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse("borrowings:borrowing-list"))
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id, self.borrowing2.id})

    def test_user_sees_only_own_borrowings(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("borrowings:borrowing-list"))
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})


class BorrowingFilterTests(BorrowingSetUp):
    def test_filter_isactive(self):
        Borrowing.objects.create(
            expected_return_date=self.expected_return_date,
            actual_return_date=self.expected_return_date,
            book=self.book,
            user=self.user
        )
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("borrowings:borrowing-list"), {"is_active": "true"})
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})
    
    def test_filter_user_id_for_admin(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse("borrowings:borrowing-list"), {"user_id": self.user.id})
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})

    def test_filter_user_id_for_user(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("borrowings:borrowing-list"), {"user_id": self.admin.id})
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})
