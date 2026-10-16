# Task Management API

A reusable Flask REST API with SQLAlchemy models, JWT authentication, task assignment, comments, pagination, filtering, input validation, rate limiting, CORS, migrations, and tests.

## Quick start

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set strong, unique `SECRET_KEY` and `JWT_SECRET_KEY` values in `.env` before deployment. The development defaults are not suitable for production. Configure the mail settings if password reset emails should be delivered; reset requests return a generic response whether or not an account exists.

Apply the included initial database migration and start the development server:

```powershell
flask --app run.py db upgrade
python run.py
```

The Flask-Migrate setup and initial schema are in `migrations/`. When models change, generate and commit a migration before upgrading:

```powershell
flask --app run.py db migrate -m "Describe schema change"
flask --app run.py db upgrade
```

For local experimentation, the app can create tables directly in a Flask shell:

```python
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    db.create_all()
```

The API is served at `http://localhost:5000`. Open the root URL (`/`) or `/docs` in a browser to view the formatted API documentation. The health check is `GET /health`. Run tests with `pytest`.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session/signing secret | development-only value |
| `JWT_SECRET_KEY` | JWT signing secret | value of `SECRET_KEY` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///tasks.db` |
| `JWT_ACCESS_MINUTES` | Access token lifetime in minutes | `15` |
| `JWT_REFRESH_DAYS` | Refresh token lifetime in days | `30` |
| `MAIL_SERVER`, `MAIL_PORT` | SMTP server and port for password reset | unset / `587` |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | SMTP credentials | unset |
| `MAIL_DEFAULT_SENDER` | Password-reset sender address | unset |
| `PASSWORD_RESET_URL` | Frontend URL receiving `?token=...` | `http://localhost:3000/reset-password` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `*` |
| `RATELIMIT_STORAGE_URI` | Flask-Limiter storage URI | `memory://` |

For multi-process production deployments, use a shared rate-limit store such as Redis instead of in-memory storage.

## API overview

API endpoints use the `/api` prefix (the `/api/v1` prefix remains as an alias). Successes use `{"status":"success","data":...}` and errors use `{"status":"error","message":"..."}` with optional field errors.

- `POST /auth/register`, `POST /auth/login`: create an account with `username`, or receive access and refresh tokens.
- `POST /auth/refresh`: exchange a refresh token for a new access token.
- `POST /auth/logout`: revoke the current access token.
- `POST /auth/password-reset/request`, `POST /auth/password-reset/confirm`: request an email reset link and set a new password.
- `GET /users/me`: retrieve the authenticated profile.
- `GET /tasks`: list owned and assigned tasks. Query parameters: `page`, `per_page` (default 10, maximum 100), `status`, `priority`, `category`, `search`, `sort_by`, `sort_order`.
- `POST /tasks`, `GET /tasks/<id>`, `PUT /tasks/<id>`, `PATCH /tasks/<id>`, `DELETE /tasks/<id>`: task lifecycle. Owners manage tasks; assignees can view tasks and add comments.
- `POST /tasks/<id>/comments`, `DELETE /tasks/<id>/comments/<comment_id>`: comment lifecycle. Authors or task owners can delete comments.

Valid statuses: `pending`, `in_progress`, `completed`. Valid priorities: `low`, `medium`, `high`. Dates accept `YYYY-MM-DD` or ISO 8601 datetimes with a timezone.

## Documentation and deployment

- OpenAPI specification: [docs/swagger.yaml](docs/swagger.yaml)
- Endpoint guide: [docs/api.md](docs/api.md)
- Project setup and coding guide: [docs/project_documentation.md](docs/project_documentation.md)
- Importable Postman collection: [docs/postman_collection.json](docs/postman_collection.json)

The included `run.py` server is for development. A production container image is defined in [Dockerfile](Dockerfile):

```powershell
docker build -t task-api .
docker run --rm -p 5000:5000 `
  -e SECRET_KEY="<strong-secret>" `
  -e JWT_SECRET_KEY="<different-strong-secret>" `
  -v task-api-data:/app/instance `
  task-api
```

Apply migrations before serving a new deployment (`flask --app run.py db upgrade`). Set production mail settings and a shared rate-limit backend (such as Redis); the default in-memory limiter is intended for development and single-process use.