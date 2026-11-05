# Vasto Workspaces API Contract

This document describes the API endpoints available to the frontend application. The frontend communicates **only** with the Workspaces backend; Workspaces handles all communication with Pwaninet internally.

## Base URL

```
http://127.0.0.1:8001/api/auth/
```

## Authentication

All endpoints require authentication via Django session cookie. The session is established after completing the OAuth flow:

1. Navigate to `/api/auth/vasto/start/` to initiate OAuth
2. Complete authentication with Pwaninet
3. Workspaces creates a session cookie (`workspaces_sessionid`)
4. All subsequent API calls use this session

**Important**: The session cookie is HttpOnly and cannot be accessed by JavaScript. The frontend should rely on the browser's automatic cookie handling.

## Response Format

All responses are JSON. Successful responses return HTTP 200 with data. Errors return appropriate HTTP status codes with error details.

```json
{
  "status": "success",
  "data": { ... }
}
```

Error responses:

```json
{
  "status": "error",
  "message": "Error description",
  "authenticated": false
}
```

---

## Authentication Endpoints

### GET `/api/auth/me/`

Get current authenticated user profile.

**Response (200):**
```json
{
  "status": "success",
  "message": "Authenticated user profile retrieved successfully.",
  "authenticated": true,
  "user": {
    "id": 1,
    "username": "john_doe",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John Doe",
    "email": "john@example.com",
    "email_verified": true,
    "profile_picture": "https://cdn.pwaninet.app/path/to/image.jpg",
    "status": "active"
  },
  "session": {
    "status": "active",
    "expires_at": "2026-11-19T00:00:00Z",
    "expires_in_seconds": 1209600
  }
}
```

**Response (401):**
```json
{
  "status": "error",
  "message": "Authentication is required.",
  "authenticated": false
}
```

### POST `/api/auth/logout/`

Log out the current user.

**Response (200):**
```json
{
  "authenticated": false,
  "logged_out": true
}
```

---

## Cached Data Endpoints

All data endpoints support `?refresh=true` query parameter to force a fresh sync from Pwaninet. Without this parameter, cached data is returned if available.

### GET `/api/auth/user/profile/`

Get user's profile data (cached from Pwaninet).

**Response (200):**
```json
{
  "id": 100,
  "username": "john_doe",
  "email": "john@example.com",
  "email_verified": true,
  "first_name": "John",
  "last_name": "Doe",
  "profile_pic": "https://cdn.pwaninet.app/path/to/image.jpg",
  "cover_photo": "https://cdn.pwaninet.app/path/to/cover.jpg",
  "bio": "Software engineering student",
  "headline": "CS Student @ Pwani University",
  "interests": "programming, technology, AI",
  "skills": ["Python", "JavaScript", "Django"],
  "projects": [
    {
      "title": "Portfolio Website",
      "description": "Personal portfolio",
      "link": "https://github.com/john/portfolio"
    }
  ],
  "github_url": "https://github.com/john",
  "linkedin_url": "https://linkedin.com/in/john",
  "portfolio_url": "",
  "twitter_url": "",
  "institution": {
    "id": 1,
    "name": "Pwani University",
    "code": "PU"
  },
  "programme": {
    "id": 11,
    "name": "Bachelor of Science in Computer Science"
  },
  "academic_level": "Year 2",
  "academic_year": "2026/2027",
  "semester": 1,
  "theme_preference": "dark",
  "language_preference": "en",
  "profile_privacy": "AUTHENTICATED",
  "is_online": true,
  "last_seen": "2026-11-05T10:30:00Z"
}
```

### GET `/api/auth/user/documents/`

Get user's documents (cached from Pwaninet).

**Response (200):**
```json
{
  "documents": [
    {
      "id": 1,
      "title": "Data Structures Notes",
      "description": "Lecture notes for CS201",
      "file_url": "https://cdn.pwaninet.app/documents/file.pdf",
      "file_type": "pdf",
      "file_size": 1024000,
      "uploaded_at": "2026-10-15T14:30:00Z",
      "updated_at": "2026-10-15T14:30:00Z",
      "category": "lecture_notes",
      "tags": ["CS201", "data-structures"],
      "institution": {
        "id": 1,
        "name": "Pwani University"
      },
      "programme": {
        "id": 11,
        "name": "Bachelor of Science in Computer Science"
      }
    }
  ]
}
```

### GET `/api/auth/user/institution/`

Get user's institution details (cached from Pwaninet).

**Response (200):**
```json
{
  "id": 1,
  "name": "Pwani University",
  "code": "PU",
  "logo": "https://cdn.pwaninet.app/institutions/logo.png",
  "description": "Leading university in coastal region",
  "location": "Kilifi, Kenya",
  "website": "https://pwaninet.app",
  "programmes": [
    {
      "id": 11,
      "name": "Bachelor of Science in Computer Science",
      "code": "BSC-CS"
    }
  ]
}
```

**Response (404):**
```json
{
  "error": "Institution not available"
}
```

### GET `/api/auth/user/courses/`

Get user's enrolled courses (cached from Pwaninet).

**Response (200):**
```json
{
  "courses": [
    {
      "id": 1,
      "name": "Data Structures and Algorithms",
      "code": "CS201",
      "description": "Introduction to data structures",
      "credits": 3,
      "institution": {
        "id": 1,
        "name": "Pwani University"
      },
      "programme": {
        "id": 11,
        "name": "Bachelor of Science in Computer Science"
      },
      "instructor": "dr_smith",
      "semester": "Semester 1",
      "enrolled_at": "2026-09-01T00:00:00Z",
      "status": "active"
    }
  ]
}
```

### GET `/api/auth/user/groups/`

Get user's group memberships (cached from Pwaninet).

**Response (200):**
```json
{
  "groups": [
    {
      "id": 1,
      "name": "Computer Science Students",
      "description": "Official CS student group",
      "type": "course",
      "created_at": "2026-09-01T00:00:00Z",
      "updated_at": "2026-10-15T14:30:00Z",
      "institution": {
        "id": 1,
        "name": "Pwani University"
      },
      "programme": {
        "id": 11,
        "name": "Bachelor of Science in Computer Science"
      },
      "role": "member",
      "joined_at": "2026-09-01T00:00:00Z"
    }
  ]
}
```

### GET `/api/auth/user/notifications/`

Get user's notifications (cached from Pwaninet).

**Response (200):**
```json
{
  "notifications": [
    {
      "id": 1,
      "type": "message",
      "message": "You have a new message from Jane",
      "actor": {
        "id": 2,
        "username": "jane_doe"
      },
      "target_type": "conversation",
      "target_id": "123",
      "is_read": false,
      "created_at": "2026-11-05T10:30:00Z"
    }
  ]
}
```

### GET `/api/auth/user/conversations/`

Get user's conversations (cached from Pwaninet).

**Response (200):**
```json
{
  "conversations": [
    {
      "id": 1,
      "type": "direct",
      "name": null,
      "participants": [
        {"id": 1, "username": "john_doe"},
        {"id": 2, "username": "jane_doe"}
      ],
      "last_message_at": "2026-11-05T10:30:00Z",
      "unread_count": 2
    }
  ]
}
```

---

## Manual Sync Endpoint

### POST `/api/auth/user/sync/`

Manually trigger data sync for the current user.

**Request Body (optional):**
```json
{
  "types": ["profile", "documents", "institution", "courses", "groups", "notifications", "conversations"]
}
```

If `types` is not provided, all data types are synced.

**Response (200):**
```json
{
  "status": "success",
  "results": {
    "profile": true,
    "documents": true,
    "institution": true,
    "courses": true,
    "groups": true,
    "notifications": true,
    "conversations": true
  },
  "message": "Sync completed"
}
```

---

## Error Handling

| Status Code | Meaning | Action |
|-------------|---------|--------|
| 200 | Success | Data returned successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | User not authenticated; redirect to login |
| 403 | Forbidden | User doesn't have permission |
| 404 | Not Found | Resource doesn't exist |
| 503 | Service Unavailable | Pwaninet is unreachable; cached data may still be available |

## Caching Behavior

- **Cache Hit**: Returns cached data immediately (fast)
- **Cache Miss**: Fetches from Pwaninet, updates cache, returns data (slower)
- **Cache Expired**: Fetches fresh data from Pwaninet
- **Pwaninet Down**: Returns stale cached data if available, or 503 error

## Best Practices

1. **Use cached data**: Don't use `?refresh=true` on every request; only when user explicitly requests fresh data
2. **Handle offline**: If API returns 503, show cached data or offline message
3. **Session management**: Check `/api/auth/me/` on app load to verify authentication
4. **Error handling**: Always handle 401 responses by redirecting to login
5. **Polling**: For real-time updates, consider WebSocket or polling with reasonable intervals

## WebSocket Support

Currently, Workspaces does not provide WebSocket endpoints. For real-time features like chat, the frontend should:
1. Poll `/api/auth/user/conversations/` periodically
2. Use `?refresh=true` for immediate updates when needed
3. Consider implementing WebSocket support in a future iteration

## Rate Limiting

No explicit rate limiting is implemented on Workspaces API endpoints. However, excessive requests may be throttled by the underlying infrastructure.

## Security Notes

- **Never expose** `VASTO_SERVICE_TOKEN` or `VASTO_CLIENT_SECRET` to the frontend
- **Session cookies** are HttpOnly and secure; do not attempt to access them via JavaScript
- **CSRF protection** is enabled for state-changing operations (POST, PUT, DELETE)
- **HTTPS** should be used in production for all API calls
