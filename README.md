# Social Media API

A production-ready RESTful Social Media API built with
**Django**, **Django REST Framework**, **JWT auth**,
**Celery**, and **drf-spectacular**.
Strict **Test-Driven Development** — 92 tests, pytest.
All CRUD resources use `ModelViewSet` + `DefaultRouter`.
`APIView` reserved for auth and toggle actions only.
Zero N+1 queries via `select_related`/`prefetch_related`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5 + DRF 3.15 |
| Auth | JWT (SimpleJWT + token blacklist) |
| Task queue | Celery 5 + Redis 7 |
| Database | PostgreSQL 16 (SQLite for dev) |
| Docs | drf-spectacular (Swagger UI) |
| Testing | pytest + pytest-django |
| Containers | Docker + Docker Compose |

---

## Features

- **Auth** — register, login, logout (JWT blacklist)
- **Profiles** — retrieve, update, search users
- **Relationships** — follow/unfollow, followers/following
- **Posts** — create, feed, own posts, hashtag filter
- **Engagement** — likes/unlikes, comments
- **Scheduled posts** — Celery publishes at future time
- **Docs** — Swagger UI at `/api/docs/`
- **N+1 free** — centralised optimised querysets

---

## Project Structure

```
social_media_api/
├── conftest.py                 # shared pytest fixtures
├── pytest.ini
├── .flake8
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
│
├── social_media_api/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── celery.py
│   ├── __init__.py
│   ├── urls.py
│   └── wsgi.py
│
├── user/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py               # RegisterView, LoginView,
│   │                          # LogoutView, UserViewSet
│   ├── permissions.py         # IsOwnerOrReadOnly
│   ├── admin.py
│   ├── urls.py
│   └── tests/
│       ├── test_auth.py
│       ├── test_profile.py
│       └── test_relationships.py
│
└── post/
    ├── models.py
    ├── serializers.py
    ├── views.py               # PostViewSet,
    │                          # CommentViewSet,
    │                          # ScheduledPostViewSet
    ├── mixins.py              # AuthorPermissionMixin
    ├── permissions.py         # IsAuthorOrReadOnly
    ├── tasks.py               # publish_scheduled_posts
    ├── admin.py
    ├── urls.py
    └── tests/
        ├── test_posts.py
        ├── test_likes_comments.py
        ├── test_scheduled.py
        └── test_schema.py
```

---

## Local Development

### 1. Clone & virtual environment

```bash
git clone https://github.com/your-username/social-media-api
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
# Set SECRET_KEY at minimum
```

### 4. Migrate & run

```bash
python manage.py migrate
python manage.py runserver
```

### 5. Celery (two separate terminals)

```bash
# Terminal 1
celery -A social_media_api worker --loglevel=info

# Terminal 2
celery -A social_media_api beat --loglevel=info
```

---

## Running Tests

```bash
pytest                        # full suite
pytest user/tests/ -v         # user app only
pytest post/tests/ -v         # post app only
pytest --tb=short             # compact output
```

---

## Docker

```bash
cp .env.example .env
docker compose up --build -d
```

| Service | Role |
|---|---|
| `web` | Gunicorn :8000 |
| `worker` | Celery worker |
| `beat` | Celery beat |
| `db` | PostgreSQL 16 |
| `redis` | Broker + backend |

---

## API Reference

```
http://127.0.0.1:8000/api/docs/    ← Swagger UI
http://127.0.0.1:8000/api/schema/  ← OpenAPI JSON
```

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/user/register/` | Register |
| POST | `/api/user/login/` | Login → tokens |
| POST | `/api/user/logout/` | Logout |

### Profiles
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/user/` | List/search users |
| GET | `/api/user/<id>/` | Retrieve profile |
| PATCH | `/api/user/<id>/` | Update (owner) |
| GET/PATCH | `/api/user/me/` | Own profile |

### Relationships
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/user/<id>/follow/` | Follow |
| POST | `/api/user/<id>/unfollow/` | Unfollow |
| GET | `/api/user/<id>/followers/` | Followers list |
| GET | `/api/user/<id>/following/` | Following list |

### Posts
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/post/` | All posts (`?hashtag=`) |
| POST | `/api/post/` | Create post |
| GET/PATCH/DELETE | `/api/post/<id>/` | Post detail |
| GET | `/api/post/my-posts/` | Own posts |
| GET | `/api/post/feed/` | Feed |

### Engagement
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/post/<id>/like/` | Like |
| POST | `/api/post/<id>/unlike/` | Unlike |
| GET/POST | `/api/post/<id>/comments/` | Comments |
| GET/PATCH/DELETE | `/api/post/<id>/comments/<id>/` | Comment detail |

### Scheduled Posts
| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/post/scheduled/` | List/create |
| GET/PATCH/DELETE | `/api/post/scheduled/<id>/` | Detail |

---

## Architecture Notes

### View layer rule
| Pattern | When used |
|---|---|
| `ModelViewSet` | All CRUD resources |
| `APIView` | Auth only (register, login, logout) |
| `@action` | Toggles and sub-resources |

### Duplication eliminated
| Problem | Solution |
|---|---|
| `get_permissions` in 3 viewsets | `AuthorPermissionMixin` |
| `http_method_names` in 3 viewsets | `AuthorPermissionMixin` |
| `like`/`unlike` mirror logic | `_like_response(action)` |
| `follow`/`unfollow` mirror logic | `_follow_response(action)` |
| `followers`/`following` mirror logic | `_follow_list_response(relation)` |
| Fixtures in 7 test files | `conftest.py` |

### N+1 prevention
| ViewSet | Fix |
|---|---|
| `PostViewSet` | `select_related("author")` + `prefetch_related("author__followers", "author__following", "hashtags", "likes", "comments")` |
| `CommentViewSet` | `select_related("author")` + `prefetch_related("author__followers", "author__following")` |
| `UserViewSet` | `prefetch_related("followers", "following")` |
| Celery task | `select_related("author")` |

---

## Test Coverage

| File | Tests |
|---|---|
| `test_auth.py` | 8 |
| `test_profile.py` | 8 |
| `test_relationships.py` | 16 |
| `test_posts.py` | 20 |
| `test_likes_comments.py` | 17 |
| `test_scheduled.py` | 10 |
| `test_schema.py` | 13 |
| **Total** | **92** |

---

## Commit History

```
chore: initial project setup
feat: custom User model, JWT auth
feat: profile endpoints
feat: follow/unfollow, followers/following
feat: posts, feed, hashtag filter
feat: likes, comments, celery scheduled posts
docs: drf-spectacular OpenAPI schema
chore: production hardening, Docker, README
refactor: ModelViewSet + DefaultRouter
refactor: eliminate duplicate code, add conftest
```
