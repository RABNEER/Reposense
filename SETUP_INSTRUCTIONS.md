# RepoSense - Complete Setup Instructions

> **🎉 ATTENTION JUDGES**
> If you are evaluating this project for the **IBM Bob Hackathon**, you do NOT need to follow these instructions!
> The live deployment at [https://reposense-blond.vercel.app](https://reposense-blond.vercel.app) is fully configured with our own IBM WatsonX and GitHub credentials.
> Simply open the URL and use the app immediately!

---

If you wish to run the project locally for development purposes, follow these steps.

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

### Step 2: Configure Environment Variables

In the `backend` directory, create a `.env` file (you can copy `.env.example`):

```bash
# Required for WatsonX Granite integration
GROQ_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_here
```

### Step 3: Install Frontend Dependencies

Open a **new terminal** and run:

```bash
cd reposense/frontend

# Install dependencies
npm install
```

### Step 4: Start the Backend Server

In the **first terminal** (with virtual environment activated):

```bash
cd reposense/backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Start the Frontend Server

In the **second terminal**:

```bash
cd reposense/frontend
npm run dev
```

### Step 6: Open the Application

Open your browser and go to: **http://localhost:5173**

## 🎯 Test the Application

1. **Try an example repository:**
   - Paste: `https://github.com/facebook/react`
   - Click "Analyze Repository"
   - Wait 15-30 seconds for IBM Bob (WatsonX) to analyze

2. **Explore features:**
   - View the comprehensive onboarding report
   - Ask questions in the Q&A section
   - Use Task Kickstarter to plan implementations
   - Export the report as Markdown

## 📝 Example Repositories to Try

- **React**: `https://github.com/facebook/react`
- **Vue.js**: `https://github.com/vuejs/vue`
- **Express**: `https://github.com/expressjs/express`
- **FastAPI**: `https://github.com/tiangolo/fastapi`

---

**Need Help?** Check the main README.md or open an issue on GitHub.