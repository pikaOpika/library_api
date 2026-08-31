from django.db import models
from django.db.models import Q, F
from django.conf import settings

from datetime import date

from books.models import Book



class Borrowing(models.Model):
    borrow_date = models.DateField(default=date.today)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(borrow_date__lte=F("expected_return_date")),
                name="expected_return_after_borrow" 
            ),
            models.CheckConstraint(
                condition=Q(borrow_date__lte=F("actual_return_date")),
                name="actual_return_after_borrow" 
            )
        ]
