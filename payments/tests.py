from rest_framework.test import APITestCase
from rest_framework import status

from django.contrib.auth import get_user_model
from django.urls import reverse

from datetime import date

from unittest.mock import patch

from borrowings.models import Borrowing
from payments.models import Payment
from books.models import Book


class PaymentSetUp(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@gmail.com", password="user"
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
        self.borrowing_user = Borrowing.objects.create(
            expected_return_date=date.today(), book=self.book, user=self.user
        )
        self.borrowing_admin = Borrowing.objects.create(
            expected_return_date=date.today(), book=self.book, user=self.admin
        )
        self.payment_user = Payment.objects.create(
            borrowing=self.borrowing_user,
            type=Payment.Type.PAYMENT,
            money_to_pay=10,
        )
        self.payment_admin = Payment.objects.create(
            borrowing=self.borrowing_admin, type=Payment.Type.PAYMENT, money_to_pay=10
        )


class PaymentVisibilityTests(PaymentSetUp):
    def test_admin_sees_all_payments(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(reverse("payments:payment-list"))
        self.assertEqual(
            {item["id"] for item in res.data},
            {self.payment_admin.id, self.payment_user.id},
        )

    def test_user_sees_only_own_payments(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("payments:payment-list"))
        self.assertEqual({item["id"] for item in res.data}, {self.payment_user.id})


class PaymentRenewTests(PaymentSetUp):
    def renew_url(self, payment_id):
        return reverse("payments:payment-renew", kwargs={"pk": payment_id})

    def test_cannot_renew_pending_payment(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(self.renew_url(self.payment_user.id))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_renew_someone_elses_payment(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(self.renew_url(self.payment_admin.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @patch("payments.stripe_service.build_stripe_session")
    def test_renew_expired_payment(self, mock_build):
        mock_build.return_value.id = "cs_test_new"
        mock_build.return_value.url = "https://checkout.stripe.com/new"
        self.payment_user.status = Payment.Status.EXPIRED
        self.payment_user.save()
        self.client.force_authenticate(self.user)
        res = self.client.post(self.renew_url(self.payment_user.id))
        self.payment_user.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.payment_user.status, Payment.Status.PENDING)
        self.assertEqual(self.payment_user.session_id, "cs_test_new")


class PaymentSuccessTests(PaymentSetUp):
    @patch("payments.views.send_telegram_message")
    @patch("payments.views.get_stripe_session")
    def test_successful_payment_is_marked_paid(self, mock_session, mock_telegram):
        self.payment_user.session_id = "cs_test_123"
        self.payment_user.save()
        mock_session.return_value.payment_status = "paid"
        res = self.client.get(reverse("payments:payment-success"), {"session_id": "cs_test_123"})
        self.payment_user.refresh_from_db()
        mock_telegram.assert_called_once()
        self.assertEqual(self.payment_user.status, Payment.Status.PAID)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


    @patch("payments.views.send_telegram_message")
    @patch("payments.views.get_stripe_session")
    def test_repeated_success_does_not_notify_twice(self, mock_session, mock_telegram):
        self.payment_user.session_id="cs_test_123"
        self.payment_user.save()
        mock_session.return_value.payment_status="paid"
        self.client.get(reverse("payments:payment-success"), {"session_id": "cs_test_123"})
        res = self.client.get(reverse("payments:payment-success"), {"session_id": "cs_test_123"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_telegram.assert_called_once()
