# RepoSense Deployment Guide 🚀

This guide covers deploying RepoSense to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Docker Deployment](#docker-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Production Checklist](#production-checklist)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker and Docker Compose installed
- IBM Bob API key
- Domain name (optional)
- SSL certificate (recommended)

## Environment Variables

### Backend (.env)

```bash
# Required
IBM_BOB_API_KEY=your_production_api_key
IBM_BOB_API_URL=https://bob-api.ibm.com

# Environment
ENVIRONMENT=production

# CORS (update with your frontend domain)
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Optional
IBM_BOB_TIMEOUT=60
IBM_BOB_MAX_RETRIES=3
LOG_LEVEL=info
```

### Frontend (.env)

```bash
# API URL (update with your backend domain)
VITE_API_URL=https://api.your-domain.com

# Application
VITE_APP_NAME=RepoSense
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_DEBUG=false
```

## Docker Deployment

### Option 1: Docker Compose (Recommended)

**1. Clone repository:**
```bash
git clone https://github.com/yourusername/reposense.git
cd reposense
```

**2. Configure environment:**
```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with production values

# Frontend
cp frontend/.env.example frontend/.env
# Edit frontend/.env with production values
```

**3. Build and run:**
```bash
docker-compose up -d --build
```

**4. Verify deployment:**
```bash
# Check containers
docker-compose ps

# Check logs
docker-compose logs -f

# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost:5173
```

**5. Stop services:**
```bash
docker-compose down
```

### Option 2: Individual Docker Containers

**Backend:**
```bash
cd backend

# Build image
docker build -t reposense-backend .

# Run container
docker run -d \
  --name reposense-backend \
  -p 8000:8000 \
  -e IBM_BOB_API_KEY=your_key \
  -e IBM_BOB_API_URL=https://bob-api.ibm.com \
  -e ENVIRONMENT=production \
  reposense-backend
```

**Frontend:**
```bash
cd frontend

# Build image
docker build -t reposense-frontend .

# Run container
docker run -d \
  --name reposense-frontend \
  -p 80:80 \
  reposense-frontend
```

## Cloud Platforms

### Railway

**Backend Deployment:**

1. Create new project on Railway
2. Connect GitHub repository
3. Select `backend` directory
4. Add environment variables:
   - `IBM_BOB_API_KEY`
   - `IBM_BOB_API_URL`
   - `ENVIRONMENT=production`
5. Deploy

**Frontend Deployment:**

1. Create new service in same project
2. Select `frontend` directory
3. Add environment variable:
   - `VITE_API_URL=https://your-backend.railway.app`
4. Deploy

### Heroku

**Backend:**

```bash
# Login to Heroku
heroku login

# Create app
heroku create reposense-backend

# Set environment variables
heroku config:set IBM_BOB_API_KEY=your_key
heroku config:set IBM_BOB_API_URL=https://bob-api.ibm.com
heroku config:set ENVIRONMENT=production

# Deploy
git subtree push --prefix backend heroku main
```

**Frontend:**

```bash
# Create app
heroku create reposense-frontend

# Set buildpack
heroku buildpacks:set heroku/nodejs

# Set environment variables
heroku config:set VITE_API_URL=https://reposense-backend.herokuapp.com

# Deploy
git subtree push --prefix frontend heroku main
```

### Vercel (Frontend)

**1. Install Vercel CLI:**
```bash
npm install -g vercel
```

**2. Deploy:**
```bash
cd frontend
vercel --prod
```

**3. Configure environment variables in Vercel dashboard:**
- `VITE_API_URL`

### AWS EC2

**1. Launch EC2 instance:**
- Ubuntu 22.04 LTS
- t2.medium or larger
- Open ports: 22, 80, 443, 8000

**2. Connect and setup:**
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repository
git clone https://github.com/yourusername/reposense.git
cd reposense

# Configure environment
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit .env files

# Deploy
docker-compose up -d --build
```

**3. Setup Nginx reverse proxy:**
```bash
sudo apt install nginx -y

# Create Nginx config
sudo nano /etc/nginx/sites-available/reposense
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/reposense /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**4. Setup SSL with Let's Encrypt:**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### Google Cloud Run

**Backend:**

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/reposense-backend backend/

# Deploy
gcloud run deploy reposense-backend \
  --image gcr.io/PROJECT_ID/reposense-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars IBM_BOB_API_KEY=your_key,ENVIRONMENT=production
```

**Frontend:**

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/reposense-frontend frontend/

# Deploy
gcloud run deploy reposense-frontend \
  --image gcr.io/PROJECT_ID/reposense-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars VITE_API_URL=https://backend-url.run.app
```

## Production Checklist

### Security

- [ ] Use HTTPS/SSL certificates
- [ ] Set strong environment variables
- [ ] Enable CORS only for trusted domains
- [ ] Keep dependencies updated
- [ ] Use secrets management (AWS Secrets Manager, etc.)
- [ ] Enable rate limiting
- [ ] Set up firewall rules
- [ ] Regular security audits

### Performance

- [ ] Enable caching (Redis/Memcached)
- [ ] Use CDN for static assets
- [ ] Enable gzip compression
- [ ] Optimize Docker images
- [ ] Set up load balancing
- [ ] Configure auto-scaling
- [ ] Database connection pooling

### Monitoring

- [ ] Set up logging (CloudWatch, Datadog, etc.)
- [ ] Configure error tracking (Sentry)
- [ ] Set up uptime monitoring
- [ ] Configure alerts
- [ ] Track API usage
- [ ] Monitor resource usage

### Backup

- [ ] Database backups
- [ ] Configuration backups
- [ ] Disaster recovery plan
- [ ] Regular backup testing

## Monitoring

### Health Checks

**Backend:**
```bash
curl https://api.your-domain.com/health
```

**Frontend:**
```bash
curl https://your-domain.com/health
```

### Logging

**View Docker logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Log aggregation with ELK Stack:**

```yaml
# docker-compose.yml addition
  elasticsearch:
    image: elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  logstash:
    image: logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:8.5.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### Metrics

**Prometheus + Grafana:**

```yaml
# docker-compose.yml addition
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

## Troubleshooting

### Backend Issues

**Container won't start:**
```bash
# Check logs
docker logs reposense-backend

# Common issues:
# - Missing environment variables
# - Port already in use
# - Invalid IBM Bob API key
```

**API errors:**
```bash
# Check health endpoint
curl http://localhost:8000/health

# Check API docs
curl http://localhost:8000/docs

# Verify environment variables
docker exec reposense-backend env | grep IBM_BOB
```

### Frontend Issues

**Build fails:**
```bash
# Check Node version
node --version  # Should be 18+

# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check environment variables
cat .env
```

**Can't connect to backend:**
```bash
# Verify VITE_API_URL
echo $VITE_API_URL

# Test backend directly
curl http://localhost:8000/health

# Check CORS settings in backend
```

### Docker Issues

**Out of disk space:**
```bash
# Clean up
docker system prune -a

# Remove unused volumes
docker volume prune
```

**Network issues:**
```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

## Scaling

### Horizontal Scaling

**Multiple backend instances:**
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
    # ... rest of config
```

**Load balancer (Nginx):**
```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

### Vertical Scaling

**Increase resources:**
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Maintenance

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Verify
docker-compose ps
```

### Database Migrations

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Rollback if needed
docker-compose exec backend alembic downgrade -1
```

## Support

- **Documentation**: [README.md](./README.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/reposense/issues)
- **Email**: support@reposense.dev

---

Built with ❤️ for IBM Bob Hackathon 2024