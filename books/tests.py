from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book


class BookPermissionsTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com", password="a"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@gmail.com", password="admin"
        )
        self.payload = {
            "title": "Test",
            "author": "1",
            "cover": "SOFT",
            "inventory": 5,
            "daily_fee": "10.20",
        }

    def test_anonymous_get_books(self):
        res = self.client.get(reverse("books:book-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_user_create_book(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(reverse("books:book-list"), self.payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_create_book(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(reverse("books:book-list"), self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), 1)
        book = Book.objects.first()
        self.assertEqual(book.title, self.payload["title"])
