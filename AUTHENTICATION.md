# Oxide Authentication Guide

## Overview

Oxide supports JWT-based authentication with API keys for programmatic access. Authentication is **optional by default** and can be enabled via environment variable.

## Quick Start

### Default Credentials

When you first start Oxide, a default admin user is created:

```
Username: admin
Password: oxide_admin_2025
```

⚠️ **IMPORTANT**: Change this password immediately in production!

### Enable Authentication

Set the environment variable to enable authentication:

```bash
export OXIDE_AUTH_ENABLED=true
```

Or in your shell configuration:

```bash
# ~/.bashrc or ~/.zshrc
export OXIDE_AUTH_ENABLED=true
```

## Authentication Methods

### 1. JWT Bearer Tokens (for Web UI)

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "oxide_admin_2025"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Use Token:**
```bash
curl http://localhost:8000/api/services \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### 2. API Keys (for CLI/MCP)

**Generate API Key:**
```bash
curl -X POST "http://localhost:8000/auth/api-keys?name=my-cli-key" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response:**
```json
{
  "key": "ox_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789",
  "name": "my-cli-key",
  "created_at": "2025-12-27T12:00:00",
  "message": "⚠️ Store this key securely. It will not be shown again!"
}
```

**Use API Key:**
```bash
curl http://localhost:8000/api/services \
  -H "X-API-Key: ox_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
```

## User Management

### Create New User (Admin Only)

```bash
curl -X POST "http://localhost:8000/auth/users" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "password": "secure_password_123",
    "email": "dev@example.com",
    "full_name": "Developer User",
    "is_admin": false
  }'
```

### Get Current User Info

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Security Features

### Rate Limiting

- **Login**: 5 attempts per minute (prevents brute force)
- **API Key Creation**: 10 keys per hour (prevents abuse)
- Rate limits are per IP address

### Password Security

- Bcrypt hashing with automatic salt generation
- Minimum 8 character password requirement
- Password never stored in plain text

### Token Security

- HS256 algorithm (HMAC with SHA-256)
- Configurable expiration (default: 30 minutes)
- Stateless - no server-side session storage

### CORS Configuration

Allowed origins (development):
- `http://localhost:3000` (React dev)
- `http://localhost:5173` (Vite dev)
- `http://localhost:8000` (FastAPI)
- `http://127.0.0.1:8000`

For production, update `main.py` to restrict to your domain.

## Configuration

### Environment Variables

```bash
# Enable/disable authentication
export OXIDE_AUTH_ENABLED=true

# JWT secret key (change in production!)
export OXIDE_SECRET_KEY=your-secret-key-here

# Token expiration in minutes
export OXIDE_TOKEN_EXPIRE_MINUTES=30
```

### Generating Secure Secret Key

```python
import secrets
print(secrets.token_urlsafe(32))
```

Or via command line:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Protected Routes

When `OXIDE_AUTH_ENABLED=true`, these routes require authentication:

- `POST /api/tasks/*` - Task execution
- `POST /api/routing/*` - Routing rules
- `POST /api/config/*` - Configuration changes
- All `/api/*` routes (except read-only GET requests)

### Public Routes (Always Accessible)

- `POST /auth/login` - Login
- `GET /health` - Health check
- `GET /` - Web UI
- `GET /docs` - API documentation

## Role-Based Access Control

### User Roles

1. **Admin**
   - Create/manage users
   - Full API access
   - Configuration changes

2. **User** (Standard)
   - Execute tasks
   - View metrics
   - Generate personal API keys

### Admin-Only Endpoints

- `POST /auth/users` - Create user
- `PUT /api/config/*` - Modify configuration

## Best Practices

### Production Deployment

1. **Change default password immediately**
   ```bash
   # TODO: Implement password change endpoint
   ```

2. **Set secure secret key**
   ```bash
   export OXIDE_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

3. **Enable authentication**
   ```bash
   export OXIDE_AUTH_ENABLED=true
   ```

4. **Use HTTPS**
   - JWT tokens sent in plain text over HTTP can be intercepted
   - Use reverse proxy (nginx/traefik) with SSL/TLS

5. **Restrict CORS origins**
   - Update `allow_origins` in `main.py` to your domain only

### API Key Management

- Generate separate keys for different applications
- Use descriptive names (`my-cli-tool`, `production-api`, etc.)
- Rotate keys regularly
- Revoke compromised keys immediately

### Monitoring

- Check failed login attempts
- Monitor API key usage
- Review user access logs

## Troubleshooting

### "Authentication required" error

1. Check if auth is enabled: `echo $OXIDE_AUTH_ENABLED`
2. Verify token/API key is valid
3. Check token expiration (default: 30 minutes)

### Rate limit exceeded

- Wait for rate limit window to reset
- For login: wait 1 minute
- For API keys: wait 1 hour

### Invalid credentials

- Verify username and password
- Check if user account is disabled
- Ensure password meets minimum length (8 characters)

## Migration from Unauthenticated

If upgrading from version without auth:

1. Authentication is **disabled by default** - existing setups continue to work
2. Enable when ready: `export OXIDE_AUTH_ENABLED=true`
3. Update clients to use JWT tokens or API keys
4. No database migration needed - uses separate JSON files

## Storage

Authentication data stored in:
- `~/.oxide/users.json` - User accounts
- `~/.oxide/api_keys.json` - API keys

⚠️ **Note**: Will migrate to SQLite in future release (YAY-7)

## Future Enhancements

- [ ] OAuth2 support (Google, GitHub)
- [ ] Password reset flow
- [ ] Multi-factor authentication (MFA)
- [ ] Audit logs
- [ ] Session management
- [ ] User invitation system
