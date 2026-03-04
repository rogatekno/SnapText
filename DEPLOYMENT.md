# Deployment Guide - SnapText OCR Service

## Coolify Deployment

This deployment is optimized for **Coolify** - a self-hosted PaaS platform.

### Quick Start with Coolify

#### 1. Prepare Your Repository

```bash
# Ensure these files are in your repository
- Dockerfile
- docker-compose.yml
- .env.production.example
```

#### 2. Deploy via Coolify

1. **Add New Project in Coolify**
   - Choose your Git repository
   - Select branch (e.g., `main` or `develop`)

2. **Configure Service**
   - **Builder**: Docker Compose
   - **Compose File**: `docker-compose.yml` (auto-detected)

3. **Set Environment Variables** in Coolify UI

Copy from `.env.production.example`:
```
APP_NAME=SnapText
ENVIRONMENT=production
DEBUG=false
PORT=8000
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["https://yourdomain.com"]
MAX_UPLOAD_SIZE_MB=10
LOG_LEVEL=INFO
LOG_FORMAT=json
PADDLEOCR_LANG=en
INFERENCE_ENFORCE_USE_ONEDNN=0
FLAGS_use_mkldnn=false
XLAN_ENABLE=0
```

4. **Deploy**
   - Click "Deploy" button
   - Coolify will handle SSL, reverse proxy, and networking automatically

### Coolify Resource Configuration

#### For Development/Testing (Small VPS)
```yaml
# In Coolify Service Settings -> Resource Limits
Memory Limit: 512MB - 1GB
CPU Limit: 0.5 - 1 vCPU
```

#### For Production (Recommended)
```yaml
# In Coolify Service Settings -> Resource Limits
Memory Limit: 2GB - 4GB
CPU Limit: 1 - 2 vCPU
```

## Recommended Coolify Server Sizes

### For Small Projects
- **Hetzner CX22** (2 vCPU, 4 GB RAM) - €4.65/month
- **DigitalOcean Droplet S-2vCPU-4GB** - $24/month
- **AWS t3.medium** (2 vCPU, 4 GB RAM) - ~$30/month

### For Medium Projects
- **Hetzner CX31** (2 vCPU, 8 GB RAM) - €9.35/month
- **DigitalOcean Droplet S-4vCPU-8GB** - $48/month
- **AWS t3.large** (2 vCPU, 8 GB RAM) - ~$60/month

## Environment Variables for Coolify

Set these in Coolify under **Service Settings** → **Environment Variables**:

### Required
```bash
ENVIRONMENT=production
DEBUG=false
```

### PaddlePaddle CRITICAL (Do NOT change)
```bash
INFERENCE_ENFORCE_USE_ONEDNN=0
FLAGS_use_mkldnn=false
XLAN_ENABLE=0
```

### CORS (Set your actual domain)
```bash
CORS_ORIGINS=["https://your-app.coolify.example.com"]
# OR for multiple domains:
CORS_ORIGINS=["https://app1.com","https://app2.com"]
```

### Performance Tuning
```bash
REQUEST_TIMEOUT_SECONDS=60
MAX_UPLOAD_SIZE_MB=10
WORKERS=1
```

## Coolify-Specific Configuration

### Domain Configuration
1. Go to **Service Settings** → **Domains**
2. Add your custom domain or use Coolify's generated domain
3. Coolify automatically:
   - ✅ Sets up SSL (Let's Encrypt)
   - ✅ Configures reverse proxy (Traefik)
   - ✅ Handles HTTP → HTTPS redirect
   - ✅ Manages load balancing

### Health Check
Coolify automatically checks: `http://your-service/api/v1/health`

### Logging
View logs in Coolify:
- **Service** → **Logs** tab
- Real-time streaming available

## Performance Tips for Coolify

### 1. Enable BuildKit (Faster Builds)
In Coolify → Service Settings → Build:
```
DOCKER_BUILDKIT=1
```

### 2. Persistent Storage (Optional)
For log persistence, add volume in Coolify:
```
/logs → /app/logs
```

### 3. Resource Limits
Always set limits in Coolify to prevent OOM:
```
Memory: 2GB
CPU: 1 vCPU
```

## Troubleshooting on Coolify

### Container Keeps Restarting

**Check Logs**:
- Go to Service → Logs tab
- Look for PaddlePaddle errors

**Common Fixes**:
1. **Out of Memory**: Increase memory limit in Coolify
2. **PaddlePaddle Error**: Ensure these env vars are set:
   ```bash
   INFERENCE_ENFORCE_USE_ONEDNN=0
   FLAGS_use_mkldnn=false
   XLAN_ENABLE=0
   ```

### Slow Performance

**For t3 instances**:
- Check CPU credit balance
- Consider t3a (AMD) for ~10% better price/performance

**General optimization**:
```bash
# Reduce workers for small instances
WORKERS=1

# Increase timeout for large images
REQUEST_TIMEOUT_SECONDS=90
```

### CORS Errors

Update in Coolify:
```bash
# WRONG
CORS_ORIGINS=["*"]

# CORRECT
CORS_ORIGINS=["https://your-actual-domain.com"]
```

## Monitoring

### Via Coolify
- **Service Dashboard**: Real-time metrics
- **Logs**: Application logs
- **Resource Usage**: CPU/Memory graphs

### Health Check
```bash
curl https://your-app.coolify.example.com/api/v1/health
```

## CI/CD with Coolify

Coolify auto-deploys on git push:

```bash
# Make changes
git add .
git commit -m "feat: new feature"
git push origin main

# Coolify auto-deploys 🚀
```

### Manual Deploy
- Click "Deploy" button in Coolify
- Or set up webhook from GitHub/GitLab

## Backup Strategy

### Database Backup (if you add one later)
Configure in Coolify:
- Service → Backups → Enable
- Set retention policy

### Configuration Backup
Export your environment variables from Coolify regularly

## Security Checklist

- [ ] Set proper CORS origins (not `*`)
- [ ] Enable DEBUG=false
- [ ] Set up custom domain with SSL (auto by Coolify)
- [ ] Configure resource limits
- [ ] Monitor logs regularly
- [ ] Keep dependencies updated (redeploy)

## Example Coolify Configuration

### Service Type
- Docker Compose

### Build Context
- Root of repository

### Docker Compose
```yaml
# Automatically uses docker-compose.yml
```

### Environment Variables (Minimal)
```bash
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=["https://your-app.coolify.example.com"]
PADDLEOCR_LANG=en
INFERENCE_ENFORCE_USE_ONEDNN=0
FLAGS_use_mkldnn=false
XLAN_ENABLE=0
```

### Resource Limits (t3.medium equivalent)
```bash
Memory: 2GB
CPU: 1 vCPU
```

## Cost Optimization

### Recommended Coolify Hosts

| Provider | Instance | Specs | Cost/Month | Suitable For |
|----------|----------|-------|------------|--------------|
| Hetzner | CX22 | 2 vCPU, 4 GB | €4.65 | Small projects |
| Hetzner | CX31 | 2 vCPU, 8 GB | €9.35 | Medium projects |
| DigitalOcean | Basic-2-4GB | 2 vCPU, 4 GB | $24 | Small production |
| AWS | t3.medium | 2 vCPU, 4 GB | ~$30 | Production + AWS services |

**Best Value**: Hetzner CX31 (€9.35 ≈ $10 USD)

## Support

- **Coolify Docs**: https://coolify.io/docs
- **GitHub Issues**: https://github.com/coollabsio/coolify
- **Discord Community**: https://discord.gg/coolify
