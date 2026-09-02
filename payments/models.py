from django.db import models

from borrowings.models import Borrowing


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'Pe', 'Pending'
        PAID = 'Pa', 'Paid'

    class Type(models.TextChoices):
        PAYMENT = 'P', 'Payment'
        FINE = 'F', 'Fine'
    
    status = models.CharField(choices=Status, default=Status.PENDING, max_length=2)
    type = models.CharField(choices=Type, default=Type.PAYMENT, max_length=1)
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE, related_name="payments")
    session_url = models.URLField(max_length=500, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    money_to_pay = models.DecimalField(max_digits=7, decimal_places=2)
