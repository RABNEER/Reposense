# RepoSense Deployment Guide 🚀

This guide covers deploying RepoSense to production environments.

> **🎉 JUDGES NOTICE**
> The application is already deployed and pre-configured for the **IBM Bob Hackathon**.
> **App**: [https://reposense-blond.vercel.app](https://reposense-blond.vercel.app)
> **API**: [https://reposense-production-196a.up.railway.app](https://reposense-production-196a.up.railway.app)

---

## Environment Variables

### Backend (.env)

```bash
# Required
GROQ_API_KEY=your_production_api_key
GITHUB_TOKEN=your_github_token

# Environment
ENVIRONMENT=production

# CORS (update with your frontend domain)
CORS_ORIGINS=https://reposense-blond.vercel.app

# Optional
PORT=8000
```

### Frontend (.env)

```bash
# API URL (update with your backend domain)
VITE_API_URL=https://reposense-production-196a.up.railway.app

# Application
VITE_MOCK_MODE=false
```

## Cloud Platforms

### Railway (Backend)

**Backend Deployment:**

1. Create new project on Railway
2. Connect GitHub repository
3. Select `backend` directory as the root directory for the service.
4. Add environment variables:
   - `GROQ_API_KEY`
   - `GITHUB_TOKEN`
   - `CORS_ORIGINS=https://reposense-blond.vercel.app`
5. Deploy

### Vercel (Frontend)

**1. Connect GitHub Repository to Vercel**
- Select the `frontend` directory as the root directory.

**2. Configure environment variables in Vercel dashboard:**
- `VITE_API_URL=https://reposense-production-196a.up.railway.app`
- `VITE_MOCK_MODE=false`

**3. Deploy**

## Production Checklist

### Security

- [x] Use HTTPS/SSL certificates (Handled by Railway/Vercel)
- [x] Set strong environment variables
- [x] Enable CORS only for trusted domains
- [x] Server-side API Key Management (No keys exposed to client)

### IBM Bob Integration

- [x] IBM-branded fallback messages for rate limits and quotas
- [x] Graceful timeout handling
- [x] Multi-mode fallback checks

---

Built with ❤️ for the IBM Bob Hackathon