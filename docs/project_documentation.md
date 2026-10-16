# Task Management API — Project and Code Documentation

This guide explains how to set up, run, use, test, and extend the Flask Task Management API. It includes both the API contract and the main reusable coding patterns in the project.

## 1. Project overview

The application is a JSON REST API built with Flask. It provides:

- Username/email registration, login, JWT access and refresh tokens, logout, and password resets.
- User-owned and assigned tasks, including filtering, search, sorting, and pagination.
- Task comments with owner/assignee access rules.
- SQLAlchemy persistence and Alembic database migrations.
- Shared request validation, response formatting, authentication decorators, rate limiting, and CORS.
- A browser documentation page at `/` and `/docs`.

The canonical API prefix is `/api`. The older `/api/v1` prefix is retained as an alias.

## 2. Project structure

```text
week9-task-api/
├── app/
│   ├── __init__.py              # Flask application factory and shared handlers
│   ├── extensions.py            # Shared Flask extension instances
│   ├── models.py                # SQLAlchemy User, Task, Comment, RevokedToken
│   ├── auth/
│   │   ├── routes.py            # Registration, login, refresh, logout, reset
│   │   └── utils.py             # JWT issue and reset email helpers
│   ├── tasks/
│   │   ├── routes.py            # Task and comment endpoints
│   │   └── schemas.py           # Task response serialization
│   ├── users/
│   │   ├── routes.py            # Current user profile endpoint
│   │   └── schemas.py           # User response serialization
│   ├── utils/
│   │   ├── validators.py        # Shared input and task validation
│   │   ├── decorators.py        # Current-user and task-access checks
│   │   └── responses.py         # Shared JSON response envelopes
│   └── templates/
│       └── docs.html            # Browser-friendly API documentation page
├── docs/
│   ├── api.md                   # Concise endpoint reference
│   ├── project_documentation.md # This setup and coding guide
│   ├── postman_collection.json  # Importable Postman requests
│   └── swagger.yaml             # OpenAPI specification
├── migrations/                  # Alembic environment and version scripts
├── tests/                       # Authentication, task, and user tests
├── config.py                    # Environment-based application settings
├── run.py                       # Development server entry point
├── requirements.txt
└── .env.example
```

## 3. Requirements and setup

Python 3.10 or later is recommended. These commands use PowerShell on Windows.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set unique, strong `SECRET_KEY` and `JWT_SECRET_KEY` values in `.env`. The checked-in development defaults are not suitable for deployment.

Apply migrations and run the development server:

```powershell
flask --app run.py db upgrade
python run.py
```

Open `http://127.0.0.1:5000/` or `http://127.0.0.1:5000/docs` for the formatted browser documentation. The health check is `http://127.0.0.1:5000/health`.

Run the test suite:

```powershell
python -m pytest -q
```

## 4. Configuration

Configuration is loaded from environment variables by [config.py](../config.py). The `run.py` entry point loads `.env` using `python-dotenv`.

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask application secret | Development-only value |
| `JWT_SECRET_KEY` | JWT signing secret | `SECRET_KEY` |
| `DATABASE_URL` | SQLAlchemy connection URL | `sqlite:///tasks.db` |
| `JWT_ACCESS_MINUTES` | Access-token lifetime | `15` minutes |
| `JWT_REFRESH_DAYS` | Refresh-token lifetime | `30` days |
| `MAIL_SERVER`, `MAIL_PORT` | SMTP server and port | Unset / `587` |
| `MAIL_USE_TLS` | Use SMTP TLS | `true` |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | SMTP credentials | Unset |
| `MAIL_DEFAULT_SENDER` | Reset email sender | Unset |
| `PASSWORD_RESET_URL` | Frontend page receiving reset token | `http://localhost:3000/reset-password` |
| `CORS_ORIGINS` | Comma-separated browser origins | `*` |
| `RATELIMIT_STORAGE_URI` | Flask-Limiter backend | `memory://` |

For multiple production workers, configure a shared rate-limit backend such as Redis. Configure SMTP if users should receive password reset emails.

## 5. Application architecture and reusable code

### Application factory and extensions

`create_app(config_object)` in [app/__init__.py](../app/__init__.py) constructs the Flask application. It loads configuration, initializes extensions, registers route blueprints, and installs global HTTP/JWT error handlers. Tests pass `TestingConfig` to create isolated in-memory apps.

Extensions are created once without an app and initialized by the factory:

```python
# app/extensions.py
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
```

This pattern avoids importing a running application into model and route modules, and makes it straightforward to create multiple test or production app instances.

### Response helpers

Use the shared helpers in [app/utils/responses.py](../app/utils/responses.py) so responses retain one JSON format:

```python
return success({"id": user.id}, status=200)
return error("Validation failed", 400, details={"email": ["Email is required"]})
```

Success envelope:

```json
{"status": "success", "data": {"id": 1}}
```

Error envelope:

```json
{"status": "error", "message": "Validation failed", "errors": {"email": ["Email is required"]}}
```

### Validation helpers

[app/utils/validators.py](../app/utils/validators.py) centralizes JSON body checks, email/username validation, ISO date parsing, and task field validation. Route handlers return the resulting field errors through the shared `error()` helper.

Task status values are `pending`, `in_progress`, and `completed`; priorities are `low`, `medium`, and `high`. Task titles must be at least 3 characters. Dates accept `YYYY-MM-DD` or an ISO 8601 datetime that includes a timezone.

### Authentication and access decorators

[app/utils/decorators.py](../app/utils/decorators.py) contains reusable authorization checks:

- `@current_user_required` loads the user identified by the JWT subject and passes that user to the route.
- `@accessible_task_required()` loads the task and permits its owner or assignee.
- `@accessible_task_required(owner_only=True)` restricts task changes to the owner.

Routes should still use `@jwt_required()` to validate the token before applying these decorators.

### Models and serialization

[app/models.py](../app/models.py) defines:

- `User`: username, unique email, password hash, and creation time.
- `Task`: title, description, status, priority, category, due date, timestamps, owner, and optional assignee.
- `Comment`: comment body, author, task, and creation time.
- `RevokedToken`: JWT identifier (`jti`) for logout and single-use password reset tracking.

Passwords are hashed with Werkzeug. Never serialize or return `password_hash`. `to_dict()` methods return safe response data. `format_utc_datetime()` normalizes timestamps to ISO 8601 UTC ending in `Z`.

### Blueprint organization

Route modules are separated by feature: [auth routes](../app/auth/routes.py), [task routes](../app/tasks/routes.py), and [user routes](../app/users/routes.py). The factory registers each blueprint under `/api/...` and `/api/v1/...`.

## 6. API reference

All protected routes use this HTTP header:

```text
Authorization: Bearer <access_token>
```

### Authentication endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/register` | No | Register with `username`, `email`, and `password`; returns access and refresh tokens. |
| `POST` | `/api/auth/login` | No | Verify email/password and return tokens. |
| `POST` | `/api/auth/refresh` | Refresh token | Return a new access token. |
| `POST` | `/api/auth/logout` | Access token | Revoke the current access token. |
| `POST` | `/api/auth/password-reset/request` | No | Request reset email; does not reveal whether an account exists. |
| `POST` | `/api/auth/password-reset/confirm` | No | Set a new password with a valid, unused reset token. |

Registration example:

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

Registration returns HTTP `201`:

```json
{
  "status": "success",
  "data": {
    "message": "User registered successfully",
    "user": {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com",
      "created_at": "2024-01-25T10:30:00Z"
    },
    "access_token": "<jwt>",
    "refresh_token": "<jwt>",
    "token_type": "Bearer"
  }
}
```

Usernames are 3–30 ASCII letters, digits, or underscores. Passwords must be 8–128 characters. Duplicate emails return `409`.

### Task endpoints

| Method | Path | Access | Purpose |
|---|---|---|---|
| `GET` | `/api/tasks` | Owner or assignee | List tasks with filtering, search, sorting, and pagination. |
| `POST` | `/api/tasks` | Any authenticated user | Create a task owned by the current user. |
| `GET` | `/api/tasks/{task_id}` | Owner or assignee | Get task details and comments. |
| `PATCH` | `/api/tasks/{task_id}` | Owner | Update supplied fields. |
| `PUT` | `/api/tasks/{task_id}` | Owner | Replace task fields; title is required. |
| `DELETE` | `/api/tasks/{task_id}` | Owner | Delete task and its comments. |

Task-list query parameters:

| Parameter | Default | Accepted values / purpose |
|---|---|---|
| `page` | `1` | Page number |
| `per_page` | `10` | Items per page; maximum 100 |
| `status` | — | `pending`, `in_progress`, `completed` |
| `priority` | — | `low`, `medium`, `high` |
| `sort_by` | `created_at` | `created_at`, `due_date`, `priority` |
| `sort_order` | `desc` | `asc`, `desc` |
| `category` | — | Exact category filter |
| `search` | — | Search title, description, and category |

Example request:

```text
GET /api/tasks?page=1&per_page=10&status=in_progress&priority=high&sort_by=created_at&sort_order=desc
```

Task list response:

```json
{
  "status": "success",
  "data": {
    "tasks": [
      {
        "id": 1,
        "title": "Complete API project",
        "description": "Finish task management API",
        "status": "in_progress",
        "priority": "high",
        "due_date": "2024-02-15",
        "created_at": "2024-01-25T10:30:00Z",
        "updated_at": "2024-01-25T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "per_page": 10,
      "total_pages": 5,
      "total_items": 48,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

Create-task example:

```json
{
  "title": "Complete API project",
  "description": "Finish task management API",
  "status": "pending",
  "priority": "high",
  "due_date": "2026-10-20",
  "category": "work",
  "assignee_id": 2
}
```

`title` is required. Defaults are `status: "pending"`, `priority: "medium"`, and an empty description. `due_date` and `assignee_id` may be `null`.

### Comment endpoints

| Method | Path | Access | Purpose |
|---|---|---|---|
| `POST` | `/api/tasks/{task_id}/comments` | Task owner or assignee | Add a comment using `{"body":"Comment text"}`. |
| `DELETE` | `/api/tasks/{task_id}/comments/{comment_id}` | Comment author or task owner | Delete a comment. |

### User endpoint

`GET /api/users/me` returns the authenticated user's `id`, `username`, `email`, and `created_at`.

### Error responses

Validation errors return HTTP `400`:

```json
{
  "status": "error",
  "message": "Validation failed",
  "errors": {
    "title": [
      "Title is required",
      "Title must be at least 3 characters"
    ],
    "priority": [
      "Priority must be one of: low, medium, high"
    ]
  }
}
```

Missing/invalid JWTs return HTTP `401`:

```json
{
  "status": "error",
  "message": "Missing or invalid token"
}
```

Missing tasks return HTTP `404`:

```json
{
  "status": "error",
  "message": "Task not found"
}
```

Other statuses include `403` forbidden, `409` duplicate registration, `429` rate limit exceeded, and `500` server/database error.

## 7. Coding examples

### Add a field to a task

1. Add the SQLAlchemy column to `Task` in [app/models.py](../app/models.py).
2. Add its name and validation rules to `TASK_FIELDS` and `validate_task_payload()` in [app/utils/validators.py](../app/utils/validators.py).
3. Apply it in `apply_task_payload()` in [app/tasks/routes.py](../app/tasks/routes.py).
4. Add it to the serializer in [app/models.py](../app/models.py), and the list serializer if it should appear in task-list responses.
5. Add or update tests in [tests/test_tasks.py](../tests/test_tasks.py).
6. Generate and apply a database migration (see the next section).
7. Update [docs/api.md](./api.md) and [docs/swagger.yaml](./swagger.yaml).

### Add an endpoint

Add the route to its feature blueprint, use shared helpers, and keep authorization explicit. For example:

```python
@tasks_bp.get("/summary")
@jwt_required()
@current_user_required
def task_summary(user):
    total = Task.query.filter_by(owner_id=user.id).count()
    return success({"total_tasks": total})
```

Add the endpoint to the blueprint rather than defining routes directly in `run.py`. Add tests for the successful response, missing authentication, invalid input, and access-control cases that apply.

### Add validation

Put reusable validation in `app/utils/validators.py`. Return a mapping of field names to readable error messages, then return it from a route using:

```python
return error("Validation failed", 400, details=validation_errors)
```

The response helper converts each field's message into an array so the response remains consistent.

## 8. Database migrations

Models are in `app/models.py`; the Flask-Migrate/Alembic environment and version history are in `migrations/`.

After changing a model:

```powershell
flask --app run.py db migrate -m "Describe schema change"
flask --app run.py db upgrade
```

Inspect generated migration code before applying it to important data. Commit migration scripts alongside model changes. Useful commands:

```powershell
flask --app run.py db current
flask --app run.py db history
flask --app run.py db check
```

## 9. Testing

Tests use `TestingConfig`, an in-memory SQLite database, and Flask's test client. The fixtures create tables before each test and remove them afterward.

```powershell
python -m pytest -q
```

When adding a feature, cover:

- Success and response JSON shape.
- Missing or malformed input.
- Authentication and authorization.
- Not-found behavior and relevant edge cases.

## 10. Running and deployment

`python run.py` starts Flask on `0.0.0.0` and port `5000` (or the `PORT` environment variable). This is the development server.

For production:

1. Use HTTPS and strong, separately generated Flask/JWT secrets.
2. Use a production database and apply migrations before serving traffic.
3. Configure SMTP for password-reset messages.
4. Restrict `CORS_ORIGINS` to trusted frontend origins.
5. Configure a shared rate-limit backend for multiple workers.
6. Run behind a production WSGI server or use the provided Dockerfile.

Example Docker commands:

```powershell
docker build -t task-api .
docker run --rm -p 5000:5000 `
  -e SECRET_KEY="<strong-secret>" `
  -e JWT_SECRET_KEY="<different-strong-secret>" `
  task-api
```

## 11. Related documentation

- [Browser documentation page](http://localhost:5000/docs) (available when the local API is running).
- [API endpoint guide](./api.md).
- [OpenAPI specification](./swagger.yaml).
- [Postman collection](./postman_collection.json).
- [Project README](../README.md).
