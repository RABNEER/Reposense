# RepoSense Quick Start Guide 🚀

Get RepoSense running in under 5 minutes!

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Git

## Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/reposense.git
cd reposense
```

## Step 2: Backend Setup (2 minutes)

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Edit .env file - use mock mode for quick start
# IBM_BOB_API_KEY=mock
# IBM_BOB_API_URL=https://bob-api.ibm.com
```

**Edit `.env` file:**
```bash
# For development without IBM Bob API key
IBM_BOB_API_KEY=mock

# Or with real API key
IBM_BOB_API_KEY=your_actual_api_key_here
IBM_BOB_API_URL=https://bob-api.ibm.com
```

**Start the backend:**
```bash
uvicorn main:app --reload
```

✅ Backend running at http://localhost:8000
📚 API docs at http://localhost:8000/docs

## Step 3: Frontend Setup (2 minutes)

Open a **new terminal** (keep backend running):

```bash
# Navigate to frontend
cd reposense/frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env

# Edit .env file
# VITE_API_URL=http://localhost:8000
```

**Start the frontend:**
```bash
npm run dev
```

✅ Frontend running at http://localhost:5173

## Step 4: Try It Out! (1 minute)

1. Open http://localhost:5173 in your browser
2. Paste a GitHub repository URL (try: `https://github.com/facebook/react`)
3. Click "Analyze Repository"
4. Wait 15-30 seconds for analysis
5. Explore the onboarding report!

## Example Repositories to Try

- **React**: `https://github.com/facebook/react`
- **FastAPI**: `https://github.com/tiangolo/fastapi`
- **Vue**: `https://github.com/vuejs/vue`
- **Express**: `https://github.com/expressjs/express`
- **Django**: `https://github.com/django/django`

## Mock Mode vs Real API

### Mock Mode (Default for Quick Start)
```bash
IBM_BOB_API_KEY=mock
```
- ✅ No API key needed
- ✅ Instant responses
- ✅ Perfect for frontend development
- ⚠️ Returns sample data

### Real API Mode
```bash
IBM_BOB_API_KEY=your_actual_key
IBM_BOB_API_URL=https://bob-api.ibm.com
```
- ✅ Real AI analysis
- ✅ Accurate results
- ✅ Production-ready
- ⚠️ Requires IBM Bob API key

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check if port 8000 is available
# On Windows: netstat -ano | findstr :8000
# On macOS/Linux: lsof -i :8000
```

### Frontend won't start
```bash
# Check Node version
node --version  # Should be 18+

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check if port 5173 is available
# On Windows: netstat -ano | findstr :5173
# On macOS/Linux: lsof -i :5173
```

### CORS errors
Make sure backend `.env` has:
```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### API connection errors
Make sure frontend `.env` has:
```bash
VITE_API_URL=http://localhost:8000
```

## Next Steps

- 📖 Read the full [README.md](./README.md)
- 🔧 Check [IBM_BOB_INTEGRATION.md](./IBM_BOB_INTEGRATION.md) for API details
- 🎨 Customize the frontend in `frontend/src/`
- 🔌 Add new endpoints in `backend/routers/`
- 🚀 Deploy to production (see README.md)

## Quick Commands Reference

### Backend
```bash
# Start server
uvicorn main:app --reload

# Run tests
pytest tests/ -v

# Check code style
black . --check
flake8 .

# Format code
black .
```

### Frontend
```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Lint code
npm run lint
```

## Development Workflow

1. **Start both servers** (backend + frontend)
2. **Make changes** to code
3. **See changes instantly** (hot reload enabled)
4. **Test in browser** at http://localhost:5173
5. **Check API docs** at http://localhost:8000/docs

## Production Deployment

### Backend (Railway/Heroku)
```bash
# Build Docker image
docker build -t reposense-backend ./backend

# Run container
docker run -p 8000:8000 \
  -e IBM_BOB_API_KEY=your_key \
  reposense-backend
```

### Frontend (Vercel/Netlify)
```bash
# Build
npm run build

# Deploy dist/ folder to Vercel/Netlify
```

## Getting Help

- 📚 **Documentation**: See [README.md](./README.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/reposense/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/reposense/discussions)
- 📧 **Email**: support@reposense.dev

---

**Happy coding! 🎉**

Built with ❤️ for IBM Bob Hackathon 2024