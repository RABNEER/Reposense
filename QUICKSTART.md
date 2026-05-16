# RepoSense Quick Start Guide 🚀

Get RepoSense running in under 5 minutes!

> **🎉 PLUG & PLAY EXPERIENCE FOR JUDGES**
> If you are a judge for the **IBM Bob Hackathon**, you do not need to set this up locally!
> **Live App**: [https://reposense-blond.vercel.app](https://reposense-blond.vercel.app)
> The live deployment is pre-configured with our own IBM Watsonx and GitHub API keys. **You do not need to bring your own keys or configure any settings.** Simply open the app and experience the magic instantly.

## Prerequisites (For Local Development)

- Python 3.11 or higher
- Node.js 18 or higher
- Git

## Step 1: Clone the Repository

```bash
git clone https://github.com/RABNEER/Reposense.git
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
```

**Edit `.env` file:**
```bash
# For development with real IBM Watsonx Granite AI analysis
WATSONX_API_KEY=your_actual_api_key_here
GITHUB_TOKEN=your_github_token_here
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
cd frontend

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
5. Explore the onboarding report powered by IBM Bob & IBM Watsonx Granite!

## Example Repositories to Try

- **React**: `https://github.com/facebook/react`
- **FastAPI**: `https://github.com/fastapi/fastapi`
- **Express**: `https://github.com/expressjs/express`

## Next Steps

- 📖 Read the full [README.md](./README.md)
- 🔧 Check [IBM_BOB_INTEGRATION.md](./IBM_BOB_INTEGRATION.md) for IBM Bob architecture details
- 🎨 Customize the frontend in `frontend/src/`
- 🔌 Add new endpoints in `backend/routers/`

---

**Happy coding! 🎉**

Built with ❤️ for the IBM Bob Hackathon
