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

## Endpoint Index

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/me/` | Current authenticated user + session info |
| POST | `/api/auth/logout/` | Log out, destroy session |
| GET | `/api/auth/vasto/start/` | Initiate Vasto OAuth login (redirect) |
| GET | `/api/auth/vasto/callback/` | OAuth callback (redirect target) |
| GET | `/api/auth/user/profile/` | User profile (bio, socials, institution, programme) |
| GET | `/api/auth/user/documents/` | Documents incl. private + AI-generated, with CDN file links |
| GET | `/api/auth/user/institution/` | Institution details |
| GET | `/api/auth/user/courses/` | Enrolled courses |
| GET | `/api/auth/user/programmes/` | Academic programme(s) |
| GET | `/api/auth/user/programme-units/` | Programme units for current academic context |
| GET | `/api/auth/user/timetable/` | Class timetable(s) with schedule data |
| GET | `/api/auth/user/groups/` | Group memberships |
| GET | `/api/auth/user/notifications/` | Notifications (group, activity, social, security) |
| GET | `/api/auth/user/conversations/` | Chat conversations |
| GET | `/api/auth/user/follows/` | Followed users + follow counts |
| POST | `/api/auth/user/sync/` | Manually trigger data sync |

All `GET /api/auth/user/*` endpoints accept `?refresh=true` to force a fresh fetch from Pwaninet.

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

### GET `/api/auth/vasto/start/`

Initiate the Vasto (Pwaninet) OAuth login flow. **This is a redirect endpoint, not a JSON API** — navigate to it directly (full-page navigation, not fetch/XHR).

**Frontend usage:**
```html
<a href="/api/auth/vasto/start/">Continue with Vasto</a>
```

The backend redirects through Pwaninet's OAuth consent screen and back to `/api/auth/vasto/callback/`, which establishes the session cookie and redirects to the frontend dashboard.

### GET `/api/auth/vasto/callback/`

OAuth callback endpoint — handled entirely by the backend. The frontend should never call this directly; the browser arrives here automatically after Pwaninet authorization. On success it redirects to the frontend app URL with an authenticated session cookie set.

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

Get user's documents (cached from Pwaninet). Includes the user's private documents bound to their account, plus AI-generated documents (e.g. Spark study summaries) with CDN blob links.

**Response (200):**
```json
{
  "documents": [
    {
      "id": 61,
      "share_id": "97919f7e-c8a9-40ff-8071-19cb99de3eac",
      "title": "Ramsey Athman Shaban - Resume",
      "slug": "ramsey-athman-shaban-resume",
      "description": "AI-generated summary or document description",
      "category": {
        "id": 13,
        "name": "Other",
        "code": "other"
      },
      "language": "en",
      "visibility": "public",
      "status": "ready",
      "is_available": true,
      "is_ai_generated": false,
      "generated_format": "",
      "generated_from_message_id": null,
      "files": [
        {
          "id": 49,
          "file_url": "https://cdn.pwaninet.app/dev-uploads/media/documents/2026/10/20/file.pdf",
          "storage_path": "documents/2026/10/20/file.pdf",
          "storage_provider": "r2",
          "original_filename": "Resume.pdf",
          "mime_type": "application/pdf",
          "extension": "pdf",
          "size_bytes": 245760,
          "thumbnail_url": "https://cdn.pwaninet.app/.../thumb.jpg",
          "preview_url": "https://cdn.pwaninet.app/.../preview.jpg",
          "page_count": 2,
          "processing_status": "completed",
          "uploaded_at": "2026-10-20T10:00:00Z"
        }
      ],
      "created_at": "2026-10-20T09:55:00Z",
      "updated_at": "2026-10-20T10:00:00Z",
      "published_at": null
    }
  ]
}
```

**Field notes:**
- `visibility`: `"public"`, `"private"`, or `"restricted"` — private docs are bound to the owning user only
- `is_ai_generated`: `true` when the document was generated by Spark/Pwanimate AI
- `generated_format`: output format of AI-generated docs (e.g. `"pdf"`, `"docx"`, `"markdown"`)
- `generated_from_message_id`: ID of the Pwanimate message the doc was generated from (if any)
- `files[].file_url`: CDN blob link — use directly for download/preview; `null` while processing
- `files[].thumbnail_url` / `preview_url`: CDN links for image previews (may be `null`)

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

### GET `/api/auth/user/programmes/`

Get user's academic programme(s) (cached from Pwaninet).

**Response (200):**
```json
{
  "programmes": [
    {
      "id": 11,
      "code": "BSC-CS",
      "name": "Bachelor of Science in Computer Science",
      "slug": "bsc-cs-bachelor-of-science-in-computer-science",
      "degree_type": "BACHELOR",
      "duration_years": 4,
      "description": "Undergraduate CS program",
      "is_active": true,
      "department": {
        "id": 19,
        "code": "COMP",
        "name": "Department of Computing"
      },
      "institution": {
        "id": 1,
        "name": "Pwani University"
      },
      "is_current": true
    }
  ],
  "current_programme_id": 11
}
```

### GET `/api/auth/user/groups/`

Get user's group memberships (cached from Pwaninet).

**Response (200):**
```json
{
  "groups": [
    {
      "id": 30,
      "name": "Bachelor of Science in Computer Science - Year 1",
      "description": "Official academic hub for BSC-CS Year 1 students.",
      "is_official": true,
      "group_pic": null,
      "cover_photo": null,
      "created_at": "2026-10-18T11:33:01Z",
      "programme": {
        "id": 11,
        "code": "BSC-CS",
        "name": "Bachelor of Science in Computer Science"
      },
      "course": {
        "id": 11,
        "name": "Bachelor of Science in Computer Science",
        "code": "BSC-CS"
      },
      "year": 1,
      "role": "MEMBER",
      "status": "APPROVED",
      "joined_at": "2026-10-18T11:33:01Z"
    }
  ]
}
```

**Field notes:**
- `programme` / `course`: whichever the group is scoped to; the other is `null`
- `role`: membership role (e.g. `"MEMBER"`, `"ADMIN"`)
- `status`: `"APPROVED"` for active memberships
- `group_pic` / `cover_photo`: CDN URLs or `null`

### GET `/api/auth/user/notifications/`

Get user's notifications (cached from Pwaninet). Includes group, activity, social, academic, and security notifications.

**Response (200):**
```json
{
  "notifications": [
    {
      "id": "5090a22d-8a0f-4aef-880e-28d064268aa0",
      "type": "GROUP_ANNOUNCEMENT",
      "category": "SOCIAL",
      "priority": "NORMAL",
      "title": "New announcement in Computer Science Students",
      "summary": "Midterm study group moved to Library 2",
      "status": "DELIVERED",
      "is_read": false,
      "target_type": "Group",
      "target_id": "30",
      "context_type": "GROUP",
      "context_id": "30",
      "metadata": {
        "actor_username": "jane_doe",
        "group_name": "Computer Science Students",
        "group_id": 30
      },
      "event_count": 1,
      "created_at": "2026-11-05T10:30:00Z",
      "updated_at": "2026-11-05T10:30:00Z"
    }
  ]
}
```

**Field notes:**
- `type`: `LIKE`, `COMMENT`, `MENTION`, `GROUP`, `GROUP_ANNOUNCEMENT`, `GROUP_REQUEST`, `GROUP_APPROVED`, `GROUP_REJECTED`, `FOLLOW`, `PINCH`, `DOCUMENT`, `DOCUMENT_SHARED`, `POST_CREATED`, `SECURITY`, `SYSTEM`, `AI`, etc.
- `status`: `CREATED`, `QUEUED`, `DELIVERED`, `SEEN`, `READ`, `ARCHIVED`, `EXPIRED`
- `is_read`: convenience flag — `true` when `status` is `READ`
- `metadata`: event-specific payload — commonly contains `actor_username`, `actor_id`, `group_name`, `group_id`, `target_url`, `post_id`, etc. Use it for deep-linking and actor display
- `id` is a UUID string (not an integer)

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

### GET `/api/auth/user/programme-units/`

Get programme units (courses/modules) for the user's current academic context — programme, level, year, and semester (cached from Pwaninet).

**Response (200):**
```json
{
  "programme_units": [
    {
      "id": 31,
      "academic_unit": {
        "id": 31,
        "code": "CSC101",
        "name": "Introduction to Programming",
        "slug": "csc101-introduction-to-programming",
        "description": "Fundamental programming concepts",
        "credit_hours": 3,
        "is_active": true
      },
      "academic_level": {
        "id": 21,
        "level": 1,
        "name": "Year 1"
      },
      "academic_year": {
        "id": 12,
        "code": "2026/2027",
        "name": "2026/2027",
        "is_current": true
      },
      "semester": {
        "id": 11,
        "number": 1,
        "is_current": true,
        "academic_year": {
          "id": 12,
          "code": "2026/2027",
          "name": "2026/2027",
          "is_current": true
        }
      },
      "is_core": true,
      "is_elective": false,
      "created_at": "2026-08-12T15:34:59Z"
    }
  ]
}
```

### GET `/api/auth/user/timetable/`

Get active timetable(s) for the user's academic context (cached from Pwaninet).

**Response (200):**
```json
{
  "timetables": [
    {
      "id": 3,
      "title": "BSC-CS Year 1 Timetable (Rev 1)",
      "timetable_type": "LECTURE",
      "status": "ACTIVE",
      "revision_number": 1,
      "change_summary": "",
      "schedule_data": {
        "title": "Bachelor of Science in Computer Science (Year 1) Schedule",
        "free_slots": [
          {"day": "Monday", "day_index": 1, "start_time": "11:00", "end_time": "17:00", "duration_hours": 6.0}
        ],
        "periods": []
      },
      "source_image_url": "https://cdn.pwaninet.app/media/timetables/source.jpg",
      "programme": {
        "id": 11,
        "code": "BSC-CS",
        "name": "Bachelor of Science in Computer Science"
      },
      "academic_level": {"id": 21, "level": 1, "name": "Year 1"},
      "academic_year": {"id": 12, "code": "2026/2027", "name": "2026/2027", "is_current": true},
      "semester": {"id": 11, "number": 1, "is_current": true, "academic_year": {}},
      "created_at": "2026-08-12T15:34:59Z",
      "updated_at": "2026-10-01T09:00:00Z"
    }
  ]
}
```

**Field notes:**
- `schedule_data` is a JSON structure produced by Pwaninet's timetable parser — contains `free_slots`, class `periods`, and other schedule entries. Treat it as opaque and render defensively.
- `source_image_url`: CDN link to the uploaded timetable image (may be `null`)
- Multiple timetables may be returned (e.g. different semesters); pick by `semester`/`academic_year`

### GET `/api/auth/user/follows/`

Get users the current user follows, plus follow counts (cached from Pwaninet).

**Response (200):**
```json
{
  "follows": [
    {
      "id": 45,
      "username": "jane_doe",
      "first_name": "Jane",
      "last_name": "Doe",
      "headline": "CS Student",
      "bio": "Second year CS student",
      "profile_pic": "https://cdn.pwaninet.app/media/profile_pic/jane.jpg",
      "institution": {
        "id": 1,
        "name": "Pwani University"
      },
      "programme": {
        "id": 11,
        "name": "Bachelor of Science in Computer Science"
      },
      "is_online": true,
      "last_seen": "2026-11-05T10:30:00Z",
      "followed_at": "2026-09-01T12:00:00Z"
    }
  ],
  "following_count": 1,
  "followers_count": 5
}
```

---

## Manual Sync Endpoint

### POST `/api/auth/user/sync/`

Manually trigger data sync for the current user.

**Request Body (optional):**
```json
{
  "types": ["profile", "documents", "institution", "courses", "programmes", "groups", "notifications", "conversations", "programme_units", "timetable", "follows"]
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
    "programmes": true,
    "groups": true,
    "notifications": true,
    "conversations": true,
    "programme_units": true,
    "timetable": true,
    "follows": true
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

### Cache TTLs

| Data | TTL | Refresh cadence |
|------|-----|-----------------|
| Profile | 1 hour | Hourly sync |
| Documents | 15 min | Hourly sync |
| Institution | 24 hours | Daily sync |
| Courses | 6 hours | Daily sync |
| Programmes | 24 hours | Daily sync |
| Programme units | 6 hours | Daily sync |
| Timetable | 6 hours | Daily sync |
| Groups | 30 min | Every 6 hours |
| Notifications | 2 min | Every 2 min (active users) |
| Conversations | 5 min | Every 5 min (active users) |
| Follows | 30 min | Hourly sync |

Background Celery Beat jobs keep caches fresh automatically — the frontend does not need to poll for freshness.

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
