# 📋 TASK MANAGEMENT API DOCUMENTATION

## 🔐 AUTHENTICATION ENDPOINTS

### `POST /api/auth/register`

Register a new user.

**Request body**

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

**Response — 201 Created**

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
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

## 📝 TASK ENDPOINTS

### `GET /api/tasks`

Get a paginated list of tasks belonging to or assigned to the authenticated user. Include the access token in the `Authorization: Bearer <access_token>` header.

**Query parameters**

| Parameter | Required | Default | Description |
|---|---|---|---|
| `page` | No | `1` | Page number |
| `per_page` | No | `10` | Items per page (maximum `100`) |
| `status` | No | — | Filter by `pending`, `in_progress`, or `completed` |
| `priority` | No | — | Filter by `low`, `medium`, or `high` |
| `sort_by` | No | `created_at` | Sort by `created_at`, `due_date`, or `priority` |
| `sort_order` | No | `desc` | Sort order: `asc` or `desc` |

**Response — 200 OK**

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

## 🚨 ERROR RESPONSES

### 400 Bad Request — validation failed

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

### 401 Unauthorized

```json
{
  "status": "error",
  "message": "Missing or invalid token"
}
```

### 404 Not Found

```json
{
  "status": "error",
  "message": "Task not found"
}
```

## Additional API behavior

- The same endpoints are also available under the legacy `/api/v1` prefix.
- Registration requires a username of 3–30 letters, numbers, or underscores, a valid email address, and a password of 8–128 characters.
- Task list results contain only tasks owned by or assigned to the authenticated user.
- Task dates accept `YYYY-MM-DD` or an ISO 8601 datetime with a timezone. Datetimes are returned in UTC with a trailing `Z`.
