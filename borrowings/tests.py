from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from datetime import date, timedelta

from unittest.mock import patch

from books.models import Book
from borrowings.models import Borrowing
from payments.models import Payment


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
            user=self.user,
        )
        self.borrowing2 = Borrowing.objects.create(
            expected_return_date=self.expected_return_date,
            book=self.book,
            user=self.admin,
        )
        self.payload = {
            "expected_return_date": self.expected_return_date,
            "book": self.book.id,
        }


class BorrowingVisibilityTests(BorrowingSetUp):
    def test_admin_sees_all_borrowings(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse("borrowings:borrowing-list"))
        self.assertEqual(
            {item["id"] for item in res.data}, {self.borrowing1.id, self.borrowing2.id}
        )

    def test_user_sees_only_own_borrowings(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("borrowings:borrowing-list"))
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})


class BorrowingFilterTests(BorrowingSetUp):
    def test_is_active_filter_returns_only_open_borrowings(self):
        Borrowing.objects.create(
            expected_return_date=self.expected_return_date,
            actual_return_date=self.expected_return_date,
            book=self.book,
            user=self.user,
        )
        self.client.force_authenticate(self.user)
        res = self.client.get(
            reverse("borrowings:borrowing-list"), {"is_active": "true"}
        )
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})

    def test_filter_user_id_for_admin(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(
            reverse("borrowings:borrowing-list"), {"user_id": self.user.id}
        )
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})

    def test_filter_user_id_for_user(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(
            reverse("borrowings:borrowing-list"), {"user_id": self.admin.id}
        )
        self.assertEqual({item["id"] for item in res.data}, {self.borrowing1.id})


class BorrowingReturnTests(BorrowingSetUp):
    def return_url(self, borrowing_id):
        return reverse(
            "borrowings:borrowing-borrowing-return", kwargs={"pk": borrowing_id}
        )

    def test_owner_can_return_book(self):
        self.client.force_authenticate(self.user)
        before = self.book.inventory
        res = self.client.post(self.return_url(self.borrowing1.id))
        self.book.refresh_from_db()
        self.borrowing1.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.book.inventory, before + 1)
        self.assertIsNotNone(self.borrowing1.actual_return_date)

    def test_second_return_is_rejected(self):
        self.client.force_authenticate(self.user)
        self.client.post(self.return_url(self.borrowing1.id))
        res = self.client.post(self.return_url(self.borrowing1.id))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_return_someone_elses_borrowing(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(self.return_url(self.borrowing2.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @patch("borrowings.views.create_stripe_session")
    def test_overdue_return_creates_fine(self, mock_session):
        borrowing = Borrowing.objects.create(
            borrow_date=date.today() - timedelta(days=7),
            expected_return_date=date.today() - timedelta(days=4),
            book=self.book,
            user=self.user,
        )
        self.client.force_authenticate(self.user)
        self.client.post(self.return_url(borrowing.id))
        mock_session.assert_called_once()
        self.assertEqual(
            mock_session.call_args.kwargs["payment_type"], Payment.Type.FINE
        )

    @patch("borrowings.views.create_stripe_session")
    def test_on_time_return_creates_no_fine(self, mock_session):
        borrowing = Borrowing.objects.create(
            borrow_date=date.today() - timedelta(days=3),
            expected_return_date=date.today(),
            book=self.book,
            user=self.user,
        )
        self.client.force_authenticate(self.user)
        self.client.post(self.return_url(borrowing.id))
        mock_session.assert_not_called()


class BorrowingCreateTests(BorrowingSetUp):
    @patch("borrowings.serializers.send_telegram_message")
    @patch("borrowings.serializers.create_stripe_session")
    def test_create_borrowing_decreases_inventory(self, mock_stripe, mock_telegram):
        self.client.force_authenticate(self.user)
        inventory_before = self.book.inventory
        res = self.client.post(reverse("borrowings:borrowing-list"), self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, inventory_before - 1)
        borrowing = Borrowing.objects.get(id=res.data["id"])
        self.assertEqual(borrowing.user, self.user)

    def test_cannot_borrow_book_out_of_stock(self):
        book = Book.objects.create(
            title="Test",
            author="1",
            cover="SOFT",
            inventory=0,
            daily_fee="10.20",
        )
        self.payload["book"] = book.id
        self.client.force_authenticate(self.user)
        count_before = Borrowing.objects.count()
        res = self.client.post(reverse("borrowings:borrowing-list"), self.payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Borrowing.objects.count(), count_before)

    def test_cannot_borrow_with_past_return_date(self):
        self.payload["expected_return_date"] = date.today() - timedelta(days=1)
        self.client.force_authenticate(self.user)
        count_before = Borrowing.objects.count()
        res = self.client.post(reverse("borrowings:borrowing-list"), self.payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Borrowing.objects.count(), count_before)

    def test_cannot_borrow_with_pending_payment(self):
        Payment.objects.create(
            borrowing=self.borrowing1,
            type=Payment.Type.PAYMENT,
            money_to_pay=10,
        )
        self.client.force_authenticate(self.user)
        borrowings_before = Borrowing.objects.count()
        res = self.client.post(reverse("borrowings:borrowing-list"), self.payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Borrowing.objects.count(), borrowings_before)
