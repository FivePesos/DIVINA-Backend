# DIVINA API Endpoints

Base URL: `http://<your-ip>:5000`

---

## Authentication `/api/auth`

---

### POST `/api/auth/signup` — Register Regular User

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "johndoe@email.com",
  "password": "secret123",
  "is_dive_operator": false
}
```

**Success Response `201`:**

```json
{
  "message": "Account created successfully",
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "email": "johndoe@email.com",
    "role": "regular",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  },
  "access_token": "<token>",
  "refresh_token": "<token>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"first_name, last_name, email, and password are required"` |
| `400` | `"First and last name must be at least 2 characters"` |
| `400` | `"Password must be at least 6 characters"` |
| `400` | `"Invalid email address"` |
| `409` | `"Email already registered"` |

---

### POST `/api/auth/signup` — Register Dive Operator

**Content-Type:** `multipart/form-data`

**Request Body:**

```
first_name              = Maria
last_name               = Santos
email                   = maria@blueseadivers.com
password                = secret123
is_dive_operator        = true
bir_document            = <file: PDF, JPG, JPEG, PNG — max 5MB>
certification_document  = <file: PDF, JPG, JPEG, PNG — max 5MB>
```

**Success Response `201`:**

```json
{
  "message": "Dive operator account created. Your documents are under review. You will be notified once your account is approved.",
  "user": {
    "id": 2,
    "first_name": "Maria",
    "last_name": "Santos",
    "full_name": "Maria Santos",
    "email": "maria@blueseadivers.com",
    "role": "dive_operator",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true,
    "verification_status": "pending",
    "verified_at": null,
    "rejection_reason": null,
    "documents": [
      {
        "id": 1,
        "doc_type": "bir",
        "original_filename": "BIR_2024.pdf",
        "file_size": 204800,
        "mime_type": "application/pdf",
        "uploaded_at": "2024-01-01T00:00:00"
      },
      {
        "id": 2,
        "doc_type": "certification",
        "original_filename": "PADI_cert.jpg",
        "file_size": 102400,
        "mime_type": "image/jpeg",
        "uploaded_at": "2024-01-01T00:00:00"
      }
    ]
  },
  "access_token": "<token>",
  "refresh_token": "<token>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"bir_document is required for dive operator registration"` |
| `400` | `"certification_document is required for dive operator registration"` |
| `400` | `"BIR document: Invalid file type. Allowed: PDF, JPG, JPEG, PNG"` |
| `400` | `"BIR document: File too large. Maximum size is 5 MB"` |
| `400` | `"Certification document: Invalid file type. Allowed: PDF, JPG, JPEG, PNG"` |
| `409` | `"Email already registered"` |

---

### POST `/api/auth/login` — Login

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "email": "johndoe@email.com",
  "password": "secret123"
}
```

**Success Response `200`:**

```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "email": "johndoe@email.com",
    "role": "regular",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  },
  "access_token": "<token>",
  "refresh_token": "<token>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Dive Operator — Pending Warning `200`:**

```json
{
  "message": "Login successful",
  "warning": "Your dive operator account is still pending verification.",
  "user": { ... },
  "access_token": "<token>",
  "refresh_token": "<token>"
}
```

**Dive Operator — Rejected Warning `200`:**

```json
{
  "message": "Login successful",
  "warning": "Your account was rejected: BIR document is expired.",
  "user": { ... },
  "access_token": "<token>",
  "refresh_token": "<token>"
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"Email and password are required"` |
| `401` | `"Invalid credentials"` |
| `403` | `"Account is deactivated"` |

---

### POST `/api/auth/refresh` — Refresh Access Token

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "refresh_token": "<refresh_token>"
}
```

**Success Response `200`:**

```json
{
  "message": "Token refreshed successfully",
  "access_token": "<new_token>",
  "refresh_token": "<new_token>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"Refresh token is required"` |
| `401` | `"Refresh token has expired, please log in again"` |
| `401` | `"Invalid refresh token"` |

---

### GET `/api/auth/me` — Get Current User

**Headers:**

```
Authorization: Bearer <access_token>
```

**Success Response `200`:**

```json
{
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "email": "johndoe@email.com",
    "role": "regular",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  }
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `401` | `"Missing or invalid Authorization header"` |
| `401` | `"Access token has expired"` |

---

### POST `/api/auth/logout` — Logout

**Headers:**

```
Authorization: Bearer <access_token>
```

**Success Response `200`:**

```json
{
  "message": "Logged out successfully. Please discard your tokens."
}
```

---

## Protected `/api`

> All protected routes require:
>
> ```
> Authorization: Bearer <access_token>
> ```

---

### GET `/api/profile` — Get Profile

**Success Response `200`:**

```json
{
  "profile": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "email": "johndoe@email.com",
    "role": "regular",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  }
}
```

---

### PUT `/api/profile` — Update Profile

**Content-Type:** `application/json`

**Request Body** _(all fields optional)_**:**

```json
{
  "first_name": "Johnny",
  "last_name": "Doe",
  "email": "johnny@email.com"
}
```

**Success Response `200`:**

```json
{
  "message": "Profile updated",
  "user": {
    "id": 1,
    "first_name": "Johnny",
    "last_name": "Doe",
    "full_name": "Johnny Doe",
    "email": "johnny@email.com",
    "role": "regular",
    "created_at": "2024-01-01T00:00:00",
    "is_active": true
  }
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"First name must be at least 2 characters"` |
| `400` | `"Last name must be at least 2 characters"` |
| `400` | `"Invalid email address"` |
| `409` | `"Email already registered"` |

---

### POST `/api/change-password` — Change Password

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "current_password": "secret123",
  "new_password": "newpassword456"
}
```

**Success Response `200`:**

```json
{
  "message": "Password changed successfully"
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"current_password and new_password are required"` |
| `400` | `"New password must be at least 6 characters"` |
| `401` | `"Current password is incorrect"` |

---

### GET `/api/dashboard` — General Dashboard

**Success Response `200`:**

```json
{
  "message": "Welcome, John Doe!",
  "user_id": 1,
  "role": "regular"
}
```

---

### GET `/api/operator/dashboard` — Operator Dashboard

> Requires `role = dive_operator` AND `verification_status = approved`

**Success Response `200`:**

```json
{
  "message": "Welcome, Maria Santos!",
  "verified_at": "2024-01-05T08:30:00",
  "documents": [
    {
      "id": 1,
      "doc_type": "bir",
      "original_filename": "BIR_2024.pdf",
      "file_size": 204800,
      "mime_type": "application/pdf",
      "uploaded_at": "2024-01-01T00:00:00"
    },
    {
      "id": 2,
      "doc_type": "certification",
      "original_filename": "PADI_cert.jpg",
      "file_size": 102400,
      "mime_type": "image/jpeg",
      "uploaded_at": "2024-01-01T00:00:00"
    }
  ]
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `403` | `"Dive operator access required"` |
| `403` | `"Your dive operator account has not been approved yet."` |

---

## Admin `/api/admin`

> All admin routes require:
>
> ```
> Authorization: Bearer <admin_access_token>
> role = admin
> ```

---

### GET `/api/admin/dive-operators` — List Dive Operators

**Query Params** _(optional)_**:**

```
?status=pending     ← pending | approved | rejected
```

**Success Response `200`:**

```json
{
  "total": 2,
  "dive_operators": [
    {
      "id": 2,
      "first_name": "Maria",
      "last_name": "Santos",
      "full_name": "Maria Santos",
      "email": "maria@blueseadivers.com",
      "role": "dive_operator",
      "verification_status": "pending",
      "verified_at": null,
      "rejection_reason": null,
      "documents": [ ... ]
    }
  ]
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `401` | `"Missing or invalid Authorization header"` |
| `403` | `"Admin access required"` |

---

### GET `/api/admin/dive-operators/<id>` — Get Dive Operator

**Success Response `200`:**

```json
{
  "dive_operator": {
    "id": 2,
    "first_name": "Maria",
    "last_name": "Santos",
    "full_name": "Maria Santos",
    "email": "maria@blueseadivers.com",
    "role": "dive_operator",
    "verification_status": "pending",
    "verified_at": null,
    "rejection_reason": null,
    "documents": [ ... ]
  }
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `404` | `"Dive operator not found"` |

---

### POST `/api/admin/dive-operators/<id>/approve` — Approve Operator

**Success Response `200`:**

```json
{
  "message": "Dive operator 'Maria Santos' has been approved.",
  "dive_operator": {
    "id": 2,
    "verification_status": "approved",
    "verified_at": "2024-01-05T08:30:00",
    ...
  }
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"Dive operator is already approved"` |
| `404` | `"Dive operator not found"` |

---

### POST `/api/admin/dive-operators/<id>/reject` — Reject Operator

**Content-Type:** `application/json`

**Request Body:**

```json
{
  "reason": "BIR document is expired. Please resubmit a valid document."
}
```

**Success Response `200`:**

```json
{
  "message": "Dive operator 'Maria Santos' has been rejected.",
  "dive_operator": {
    "id": 2,
    "verification_status": "rejected",
    "rejection_reason": "BIR document is expired. Please resubmit a valid document.",
    "verified_at": null,
    ...
  }
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `400` | `"A rejection reason is required"` |
| `404` | `"Dive operator not found"` |

---

### POST `/api/admin/dive-operators/<id>/reset` — Reset to Pending

**Success Response `200`:**

```json
{
  "message": "Dive operator 'Maria Santos' reset to pending.",
  "dive_operator": {
    "id": 2,
    "verification_status": "pending",
    "rejection_reason": null,
    "verified_at": null,
    ...
  }
}
```

**Error Responses:**
| Code | Message |
|------|---------|
| `404` | `"Dive operator not found"` |

---

## Token Usage

```
Access Token  — expires in 1 hour   → use in Authorization header
Refresh Token — expires in 7 days   → use only to get a new access token
```

### Authorization Header Format

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Verification Status Flow

```
signup → pending → approved ✅ → can access /operator/dashboard
                → rejected  ❌ → shown reason on login
                → reset     ↺  → back to pending
```

---

## Document Upload Rules

| Field                    | Accepted Types      | Max Size |
| ------------------------ | ------------------- | -------- |
| `bir_document`           | PDF, JPG, JPEG, PNG | 5 MB     |
| `certification_document` | PDF, JPG, JPEG, PNG | 5 MB     |
