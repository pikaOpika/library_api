from celery import shared_task
from datetime import date

from notifications.telegram import send_telegram_message
from borrowings.models import Borrowing

@shared_task
def check_overdue_borrowings():
    borrowings = Borrowing.objects.filter(
        actual_return_date__isnull=True,
        expected_return_date__lte=date.today()
    ).select_related("book", "user")
    if borrowings:
        for borrowing in borrowings:
            send_telegram_message(
                f"Past overdue {borrowing.book.title} from user {borrowing.user.email} expected return {borrowing.expected_return_date}"
            )
    else:
        send_telegram_message("No borrowings overdue today!")
