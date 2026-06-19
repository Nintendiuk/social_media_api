# Social Media API

A production-ready RESTful Social Media API built with
**Django**, **Django REST Framework**, **JWT auth**,
**Celery**, and **drf-spectacular**.
Developed following strict **Test-Driven Development**
(88 tests, pytest).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5 + DRF 3.15 |
| Auth | JWT (SimpleJWT) |
| Task queue | Celery 5 + Redis 7 |
| Database | PostgreSQL 16 (SQLite for dev) |
| Docs | drf-spectacular (Swagger UI) |
| Testing | pytest + pytest-django |
| Containers | Docker + Docker Compose |

---

## Features

- **Auth** — register, login, logout (token blacklist)
- **Profiles** — retrieve, update, search users
- **Relationships** — follow / unfollow, list followers & following
- **Posts** — create (text + optional media), feed, own posts, hashtag filter
- **Engagement** — likes / unlikes, threaded comments
- **Scheduled posts** — Celery publishes posts at a future time
- **Docs** — Swagger UI at `/api/docs/`
- **N+1 free** — `select_related` + `prefetch_related` throughout

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Redis (or Docker)

### 1. Clone & create virtual environment

```bash
git clone https://github.com/your-username/social-media-api.git
cd social-media-api

# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements/local.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Create superuser (optional)

```bash
python manage.py createsuperuser
```

### 6. Start development server

```bash
python manage.py runserver
```

### 7. Start Celery (separate terminals)

```bash
# Terminal 1 — worker
celery -A social_media_api worker --loglevel=info

# Terminal 2 — beat scheduler
celery -A social_media_api beat --loglevel=info
```

---

## Running Tests

```bash
pytest                  # full suite
pytest user/tests/ -v   # auth + profile + relationship tests
pytest post/tests/ -v   # post + engagement + scheduled tests
pytest --tb=short       # compact output
```

---

## Docker (Production)

```bash
cp .env.example .env
# Set production values in .env

docker compose up --build -d
```

Services started:

| Service | Role |
|---|---|
| `web` | Gunicorn (4 workers) |
| `worker` | Celery worker |
| `beat` | Celery beat scheduler |
| `db` | PostgreSQL 16 |
| `redis` | Broker + result backend |

---

## API Reference

Interactive docs available at:

```
http://127.0.0.1:8000/api/docs/     ← Swagger UI
http://127.0.0.1:8000/api/schema/   ← OpenAPI JSON
```

### Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/user/register/` | Register new user |
| POST | `/api/user/login/` | Obtain JWT tokens |
| POST | `/api/user/logout/` | Blacklist refresh token |

### Profiles

| Method | Endpoint | Description |
|---|---|---|
| GET / PATCH | `/api/user/profile/me/` | Own profile |
| GET / PATCH | `/api/user/profile/<id>/` | Any user profile |
| GET | `/api/user/profile/?search=` | Search users |

### Relationships

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/user/<id>/follow/` | Follow user |
| POST | `/api/user/<id>/unfollow/` | Unfollow user |
| GET | `/api/user/<id>/followers/` | List followers |
| GET | `/api/user/<id>/following/` | List following |

### Posts

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/post/` | All posts (filter: `?hashtag=`) |
| POST | `/api/post/` | Create post |
| GET / PATCH / DELETE | `/api/post/<id>/` | Post detail |
| GET | `/api/post/my-posts/` | Own posts |
| GET | `/api/post/feed/` | Personalised feed |

### Engagement

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/post/<id>/like/` | Like post |
| POST | `/api/post/<id>/unlike/` | Unlike post |
| GET / POST | `/api/post/<id>/comments/` | List / add comments |
| GET / PATCH / DELETE | `/api/post/<id>/comments/<id>/` | Comment detail |

### Scheduled Posts

| Method | Endpoint | Description |
|---|---|---|
| GET / POST | `/api/post/scheduled/` | List / create |
| GET / PATCH / DELETE | `/api/post/scheduled/<id>/` | Detail |

---

## Project Structure

```
social_media_api/
├── social_media_api/
│   ├── settings/
│   │   ├── base.py         # shared settings
│   │   ├── local.py        # dev overrides
│   │   └── production.py   # prod overrides + security
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
├── user/
│   ├── models.py           # Custom User model
│   ├── serializers.py
│   ├── views.py            # Auth + Profile + Relationships
│   ├── permissions.py      # IsOwnerOrReadOnly
│   ├── urls.py
│   └── tests/
│       ├── test_auth.py
│       ├── test_profile.py
│       └── test_relationships.py
├── post/
│   ├── models.py           # Post, Hashtag, Like,
│   │                       # Comment, ScheduledPost
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py      # IsAuthorOrReadOnly
│   ├── tasks.py            # Celery: publish_scheduled_posts
│   ├── urls.py
│   └── tests/
│       ├── test_posts.py
│       ├── test_likes_comments.py
│       └── test_schema.py
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .flake8
├── pytest.ini
└── README.md
```

---

## N+1 Query Prevention

Every queryset that serializes related data uses
`select_related` or `prefetch_related`:

| View | Optimisation |
|---|---|
| Post list / feed | `select_related("author")` + `prefetch_related("hashtags", "likes", "comments", "author__followers", "author__following")` |
| Comment list | `select_related("author")` + `prefetch_related("author__followers", "author__following")` |
| Followers / following lists | `prefetch_related("followers", "following")` |

Without prefetching, a feed of 50 posts with nested
author + hashtags + counts would fire ~250 queries.
With prefetching it stays at ~5 regardless of page size.

---

## Commit History

```
chore: initial project setup with Django, DRF, JWT, and pytest
feat: implement custom User model with JWT registration, login, and logout
feat: add profile retrieve, update, and user search endpoints
feat: implement follow/unfollow and followers/following list endpoints
feat: implement post create, feed, own posts, and hashtag filtering
feat: add likes, comments, and celery scheduled post publishing
docs: annotate all endpoints with drf-spectacular OpenAPI schema
chore: production hardening, settings split, Docker, and README
```
