---
sidebar_position: 4
---

# Deployment Guide

Deploy Oxide to production with best practices for security, performance, and reliability.

## Deployment Options

### 1. Docker (Recommended)

Docker provides the easiest path to production deployment.

#### Build Docker Image

```bash
# Clone repository
git clone https://github.com/yayoboy/oxide.git
cd oxide

# Build image
docker build -t oxide:latest .

# Or use pre-built image from GitHub Container Registry
docker pull ghcr.io/yayoboy/oxide:latest
```

#### Run with Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  oxide:
    image: ghcr.io/yayoboy/oxide:latest
    container_name: oxide-prod
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # LLM API Keys (use secrets in production)
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}

      # Security
      - OXIDE_AUTH_ENABLED=true
      - OXIDE_JWT_SECRET=${OXIDE_JWT_SECRET}
      - OXIDE_ADMIN_PASSWORD=${OXIDE_ADMIN_PASSWORD}

      # Performance
      - OXIDE_WORKERS=4
      - OXIDE_MAX_CONNECTIONS=100

      # Logging
      - OXIDE_LOG_LEVEL=info
      - OXIDE_LOG_FILE=/app/logs/oxide.log

    volumes:
      # Configuration
      - ./config:/app/config:ro

      # Persistent data
      - oxide-data:/app/data

      # Logs
      - ./logs:/app/logs

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    networks:
      - oxide-network

  # Optional: Redis for caching
  redis:
    image: redis:7-alpine
    container_name: oxide-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - oxide-network

volumes:
  oxide-data:
  redis-data:

networks:
  oxide-network:
    driver: bridge
```

Start the stack:

```bash
# Create .env file with secrets
cat > .env <<EOF
OPENROUTER_API_KEY=your-key-here
OXIDE_JWT_SECRET=$(openssl rand -hex 32)
OXIDE_ADMIN_PASSWORD=your-secure-password
EOF

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 2. Kubernetes

For larger deployments, use Kubernetes for orchestration.

#### Create Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oxide
  labels:
    app: oxide
spec:
  replicas: 3
  selector:
    matchLabels:
      app: oxide
  template:
    metadata:
      labels:
        app: oxide
    spec:
      containers:
      - name: oxide
        image: ghcr.io/yayoboy/oxide:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENROUTER_API_KEY
          valueFrom:
            secretKeyRef:
              name: oxide-secrets
              key: openrouter-api-key
        - name: OXIDE_JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: oxide-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: oxide
spec:
  selector:
    app: oxide
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Apply the configuration:

```bash
# Create secrets
kubectl create secret generic oxide-secrets \
  --from-literal=openrouter-api-key=$OPENROUTER_API_KEY \
  --from-literal=jwt-secret=$(openssl rand -hex 32)

# Deploy
kubectl apply -f oxide-deployment.yaml

# Check status
kubectl get pods
kubectl logs -f deployment/oxide
```

### 3. Systemd Service (Linux VPS)

For traditional VPS deployment:

```bash
# Install Oxide
cd /opt
git clone https://github.com/yayoboy/oxide.git
cd oxide
uv sync --all-extras

# Build frontend
cd src/oxide/web/frontend
npm install && npm run build
```

Create `/etc/systemd/system/oxide.service`:

```ini
[Unit]
Description=Oxide LLM Orchestrator
After=network.target

[Service]
Type=simple
User=oxide
WorkingDirectory=/opt/oxide
Environment="PATH=/opt/oxide/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="OPENROUTER_API_KEY=your-key-here"
Environment="OXIDE_AUTH_ENABLED=true"
Environment="OXIDE_JWT_SECRET=your-jwt-secret"
ExecStart=/opt/oxide/.venv/bin/python -m oxide.web.backend.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
# Create user
sudo useradd -r -s /bin/false oxide
sudo chown -R oxide:oxide /opt/oxide

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable oxide
sudo systemctl start oxide

# Check status
sudo systemctl status oxide
sudo journalctl -u oxide -f
```

## Reverse Proxy Configuration

### Nginx

```nginx
upstream oxide {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name oxide.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name oxide.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/oxide.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/oxide.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/oxide-access.log;
    error_log /var/log/nginx/oxide-error.log;

    # Proxy settings
    location / {
        proxy_pass http://oxide;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running LLM requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://oxide;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Static assets
    location /assets {
        proxy_pass http://oxide;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Caddy (Simpler Alternative)

```caddyfile
oxide.yourdomain.com {
    reverse_proxy localhost:8000 {
        transport http {
            read_timeout 300s
            write_timeout 300s
        }
    }

    # Automatic HTTPS with Let's Encrypt
    tls your@email.com

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }
}
```

## Security Best Practices

### 1. Enable Authentication

```bash
export OXIDE_AUTH_ENABLED=true
export OXIDE_JWT_SECRET=$(openssl rand -hex 32)
export OXIDE_ADMIN_PASSWORD="your-secure-password"
```

### 2. Use Environment Variables for Secrets

Never commit API keys to version control:

```bash
# .env file (add to .gitignore)
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OXIDE_JWT_SECRET=...
OXIDE_ADMIN_PASSWORD=...
```

### 3. Enable Rate Limiting

Configure in `config/default.yaml`:

```yaml
security:
  rate_limiting:
    enabled: true
    default_limit: 100  # requests per minute
    authenticated_limit: 1000
```

### 4. Enable HTTPS

Always use HTTPS in production:

```bash
# Get SSL certificate with certbot
sudo certbot --nginx -d oxide.yourdomain.com
```

### 5. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## Monitoring & Logging

### Application Logs

```yaml
# config/default.yaml
logging:
  level: info
  file: /var/log/oxide/oxide.log
  console: true
  format: json  # For log aggregation
```

### Health Checks

```bash
# Endpoint for load balancers
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "orchestrator": true,
  "services": 6
}
```

### Metrics Export (Prometheus)

Coming soon: Prometheus metrics export at `/metrics`

## Performance Tuning

### 1. Worker Configuration

```bash
# Multiple workers for production
export OXIDE_WORKERS=4

# Or in config
workers: 4
```

### 2. Connection Pooling

```yaml
# config/default.yaml
http:
  pool_connections: 100
  pool_maxsize: 200
  max_retries: 3
```

### 3. Caching

Enable Redis for caching:

```yaml
cache:
  enabled: true
  backend: redis
  redis_url: redis://localhost:6379/0
  ttl: 3600
```

## Backup & Recovery

### Backup Configuration

```bash
# Backup config directory
tar -czf oxide-config-$(date +%Y%m%d).tar.gz config/

# Backup data directory
tar -czf oxide-data-$(date +%Y%m%d).tar.gz data/
```

### Database Backup (if using external DB)

```bash
# PostgreSQL
pg_dump -h localhost -U oxide oxide_db > backup.sql

# MongoDB
mongodump --db oxide --out /backup/oxide-$(date +%Y%m%d)
```

## Troubleshooting

### High Memory Usage

```bash
# Check memory usage
docker stats oxide-prod

# Reduce workers
export OXIDE_WORKERS=2
```

### Slow Response Times

1. **Enable caching**: Use Redis for response caching
2. **Increase workers**: Scale horizontally
3. **Optimize routing**: Use faster models for simple tasks

### Connection Errors

```bash
# Check service connectivity
curl http://localhost:11434/api/tags  # Ollama
curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

## Next Steps

- **[Monitoring Setup](./monitoring)** - Set up comprehensive monitoring
- **[Scaling Guide](./scaling)** - Scale Oxide for high traffic
- **[Backup Strategies](./backup)** - Implement automated backups
