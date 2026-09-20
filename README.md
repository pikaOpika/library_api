# Library Service API

REST API for a small library: books, borrowings, Stripe payments and Telegram
notifications. Built with Django REST Framework, PostgreSQL, Celery and Redis.

## Features

- JWT authentication with email instead of username
- Public book catalogue, admin-only write access
- Borrowings with race-safe inventory updates
- Stripe checkout: payment on borrowing, fine on a late return
- Renewal of expired checkout sessions
- Telegram notifications: new borrowing, successful payment, overdue books
- Scheduled Celery tasks for overdue borrowings and expired sessions
- OpenAPI schema with Swagger UI and ReDoc

## Tech stack

| Purpose | Tool |
|---|---|
| Web framework | Django 6, Django REST Framework |
| Database | PostgreSQL 16 |
| Auth | djangorestframework-simplejwt |
| Background jobs | Celery + Redis |
| Payments | Stripe (test mode) |
| Docs | drf-spectacular |
| Tests | Django test runner, coverage |
| Style | black, flake8 |

## Getting started

Requires Docker and Docker Compose.

```bash
git clone https://github.com/pikaOpika/library_api.git
cd library_api
cp .env.example .env    # fill in the values
docker compose up --build
```

The API is available at `http://localhost:8000/api/`.

Create an admin user:

```bash
docker compose exec app python manage.py createsuperuser
```

### Environment variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local development |
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_HOST` | `db` inside Docker, `localhost` outside |
| `POSTGRES_PORT` | `5432` |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` |
| `STRIPE_SECRET_KEY` | Stripe test secret key (`sk_test_...`) |
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Chat that receives notifications |
| `FINE_MULTIPLIER` | Multiplier applied to the daily fee when a book is late |

## Services

`docker compose` starts five containers:

- `app` — Django development server
- `db` — PostgreSQL
- `redis` — Celery broker
- `worker` — Celery worker
- `beat` — Celery scheduler

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/books/` | GET | List books (open to everyone) |
| `/api/books/` | POST | Create a book (admin only) |
| `/api/users/` | POST | Register |
| `/api/users/token/` | POST | Obtain a JWT pair |
| `/api/users/me/` | GET, PUT, PATCH | Own profile |
| `/api/borrowings/` | GET | Own borrowings; all of them for admins |
| `/api/borrowings/` | POST | Borrow a book |
| `/api/borrowings/{id}/return/` | POST | Return a book |
| `/api/payments/` | GET | Own payments; all of them for admins |
| `/api/payments/{id}/renew/` | POST | New checkout session for an expired payment |

Query parameters for `/api/borrowings/`:

- `is_active=true` — only borrowings that have not been returned
- `user_id=<id>` — filter by user, admins only

### Documentation

- Swagger UI: `http://localhost:8000/api/doc/swagger/`
- ReDoc: `http://localhost:8000/api/doc/redoc/`
- Raw schema: `http://localhost:8000/api/schema/`

## Borrowing flow

1. A user borrows a book. The inventory is decreased and a `PENDING` payment
   with a Stripe checkout link is created.
2. A user with an unpaid payment cannot borrow another book.
3. After payment Stripe redirects to `/api/payments/success/`. The session is
   verified with Stripe before the payment is marked as `PAID`.
4. A checkout session expires after 24 hours. A scheduled task marks such
   payments as `EXPIRED`, and the user can request a new link through
   `/api/payments/{id}/renew/`.
5. Returning a book increases the inventory. A late return creates an extra
   `FINE` payment.

## Scheduled tasks

| Task | Schedule | What it does |
|---|---|---|
| `check_overdue_borrowings` | daily | Sends a Telegram message about books that are due |
| `check_expired_payments` | every minute | Marks payments whose Stripe session has expired |

## Testing

```bash
docker compose exec app python manage.py test
```

With coverage:

```bash
docker compose exec app coverage run manage.py test
docker compose exec app coverage report
```

Current coverage: 88%.

## Code style

```bash
docker compose exec app black .
docker compose exec app flake8 .
```
