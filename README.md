# Hamilton Rec Programs — Render Deployment

A Python/Flask web app that scrapes City of Hamilton recreation program schedules
and displays them with filtering and search. Deployable to Render.com for free.

---

## Project Structure

```
hamilton_rec/
├── app.py              ← Flask app (routes + scheduler)
├── scraper.py          ← Scraper for hamilton.ca
├── templates/
│   └── index.html      ← Web dashboard
├── data/               ← Auto-created; stores programs.json
├── requirements.txt    ← Python dependencies
├── Procfile            ← Render/Heroku start command
├── .gitignore
└── README.md
```

---

## Deploying to Render.com (Free)

### Step 1 — Push to GitHub
1. Create a new GitHub repo (e.g. `hamilton-rec`)
2. In this folder, run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/hamilton-rec.git
   git push -u origin main
   ```

### Step 2 — Create a Web Service on Render
1. Go to **https://dashboard.render.com** and click **"New +"** → **"Web Service"**
2. Connect your GitHub account and select the `hamilton-rec` repo
3. Fill in the settings:
   | Field | Value |
   |---|---|
   | **Name** | `hamilton-rec` (or anything you like) |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120` |
   | **Instance Type** | `Free` |
4. Click **"Create Web Service"**

Render will build and deploy automatically. In ~2 minutes you'll get a URL like:
**`https://hamilton-rec.onrender.com`**

Share that link with anyone — no sign-in required!

### Step 3 — Done 🎉
Your app will:
- Scrape Hamilton rec programs on startup
- Re-scrape every 6 hours automatically
- Be accessible to anyone with the link

---

## ⚠️ Free Tier Note
Render's free tier **spins down after 15 minutes of inactivity**. The first visit
after a period of no traffic may take 30–60 seconds to wake up. To avoid this,
upgrade to the Starter plan ($7/mo) or use a free uptime monitor like
[UptimeRobot](https://uptimerobot.com) to ping your app every 10 minutes.

---

## Running Locally

```bash
pip install -r requirements.txt
python app.py
```
Open **http://localhost:8080**

---

## Customisation

| Setting | File | Variable |
|---|---|---|
| Refresh interval | `app.py` | `REFRESH_HOURS` |
| Add program pages | `scraper.py` | `PROGRAM_PAGES` |
| Add rec centres | `scraper.py` | `CENTRE_PAGES` |
