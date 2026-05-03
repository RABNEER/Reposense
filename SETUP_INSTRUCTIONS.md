# RepoSense - Complete Setup Instructions

Your IBM Bob API key has been configured! Follow these steps to run the application.

## ✅ Prerequisites Installed
- Python 3.9+
- Node.js 18+
- npm

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Backend Dependencies

Open a terminal and run:

```bash
cd reposense/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt):
venv\Scripts\activate.bat

# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Install Frontend Dependencies

Open a **new terminal** and run:

```bash
cd reposense/frontend

# Install dependencies
npm install
```

### Step 3: Start the Backend Server

In the **first terminal** (with virtual environment activated):

```bash
cd reposense/backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 4: Start the Frontend Server

In the **second terminal**:

```bash
cd reposense/frontend
npm run dev
```

You should see:
```
  VITE v5.0.11  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

### Step 5: Open the Application

Open your browser and go to: **http://localhost:3000**

## 🎯 Test the Application

1. **Try an example repository:**
   - Paste: `https://github.com/facebook/react`
   - Click "Analyze Repository"
   - Wait 15-30 seconds for IBM Bob to analyze

2. **Explore features:**
   - View the comprehensive onboarding report
   - Ask questions in the Q&A section
   - Use Task Kickstarter to plan implementations
   - Export the report as Markdown or PDF

## 📝 Example Repositories to Try

- **React**: `https://github.com/facebook/react`
- **Vue.js**: `https://github.com/vuejs/vue`
- **Express**: `https://github.com/expressjs/express`
- **FastAPI**: `https://github.com/tiangolo/fastapi`
- **Next.js**: `https://github.com/vercel/next.js`

## 🔧 Troubleshooting

### Backend Issues

**Error: "ModuleNotFoundError"**
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

**Error: "Port 8000 already in use"**
- Stop any other process using port 8000
- Or change port: `uvicorn main:app --reload --port 8001`

**Error: "BOB_API_KEY not found"**
- Check that `.env` file exists in `backend/` directory
- Verify the API key is correctly set

### Frontend Issues

**Error: "Cannot find module"**
- Delete `node_modules` folder
- Run `npm install` again

**Error: "Port 3000 already in use"**
- The dev server will automatically try port 3001
- Or manually specify: `npm run dev -- --port 3001`

**Error: "Failed to fetch"**
- Make sure backend is running on port 8000
- Check browser console for CORS errors

## 🎨 API Endpoints

Once running, you can access:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

## 📚 Additional Resources

- **README.md** - Complete project documentation
- **QUICKSTART.md** - Quick reference guide
- **IBM_BOB_INTEGRATION.md** - How IBM Bob powers the app

## 🎉 You're Ready!

Your RepoSense application is now fully configured and ready to use. Start analyzing repositories and see how IBM Bob helps you understand codebases in minutes!

---

**Need Help?** Check the main README.md or open an issue on GitHub.