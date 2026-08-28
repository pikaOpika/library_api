from django.db import models


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "H", "Hard"
        SOFT = "S", "Soft"

    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    cover = models.CharField(max_length=1, choices=Cover, default=Cover.SOFT)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=5, decimal_places=2)


    def __str__(self):
        return f"Book {self.title}"

    class Meta:
        ordering = ["title"]
