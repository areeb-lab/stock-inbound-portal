# 🚚 Fleek-Inbound Setup Guide

## File Structure
```
fleek-inbound/
├── app.py              ← Flask backend
├── requirements.txt    ← Python packages
├── Procfile            ← Render start command
└── static/
    └── index.html      ← Frontend (HTML/CSS/JS)
```

---

## STEP 1: Google Service Account Setup

### 1.1 Google Cloud Console
1. **google.com/cloud** → Sign in with your Google account
2. **New Project** banao → Name: `fleek-inbound` → **Create**
3. Left menu → **APIs & Services** → **Enable APIs and Services**
4. Search karo **Google Sheets API** → Enable karo
5. Search karo **Google Drive API** → Enable karo

### 1.2 Service Account banana
1. Left menu → **APIs & Services** → **Credentials**
2. **+ CREATE CREDENTIALS** → **Service Account**
3. Name: `fleek-inbound-sa` → **Create and Continue** → **Done**
4. Service account pe click karo → **KEYS** tab
5. **ADD KEY** → **Create new key** → **JSON** → **Create**
6. JSON file download ho jayegi — **sambhal ke rakho!**

### 1.3 Google Sheet Share karo
1. Apni Google Sheet kholo
2. Top-right **Share** button → Service account ki email paste karo
   (JSON file mein `client_email` field mein milegi, kuch aisa: `fleek-inbound-sa@fleek-inbound.iam.gserviceaccount.com`)
3. Role: **Editor** → **Send**

---

## STEP 2: GitHub Repository

1. **github.com** → New Repository → Name: `fleek-inbound` → **Create**
2. Apne computer pe yeh folder upload karo:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `static/index.html`

### Ya Terminal se:
```bash
cd fleek-inbound
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/fleek-inbound.git
git push -u origin main
```

---

## STEP 3: Render.com Deploy

1. **render.com** → Sign up (GitHub se login karo)
2. **New** → **Web Service**
3. GitHub repo connect karo → `fleek-inbound` select karo
4. Settings:
   - **Name:** `fleek-inbound`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Plan:** Free

### Environment Variables (IMPORTANT):
**Environment** tab mein yeh 3 variables add karo:

| Key | Value |
|-----|-------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | (pura JSON file ka content paste karo — ek line mein) |
| `GOOGLE_SHEET_ID` | (Sheet URL mein se ID: `docs.google.com/spreadsheets/d/`**ID**`/edit`) |
| `IMGBB_API_KEY` | (imgbb.com → Account → API → your key) |

### JSON ek line mein kaise karo?
JSON file open karo, pura content copy karo aur yahan paste karo:
https://jsonformatter.org/ → Compress karo → phir paste karo

5. **Create Web Service** → Deploy hoga (2-3 minutes)
6. URL milega: `https://fleek-inbound.onrender.com`

---

## STEP 4: ImgBB API Key

1. **imgbb.com** → Sign up/Login
2. Top-right apna name → **API**
3. API key copy karo → Render environment variable mein paste karo

---

## Done! 🎉

App open karo: `https://fleek-inbound.onrender.com`

---

## Troubleshooting

**Orders load nahi ho rahe?**
- Check karo service account ko sheet share ki hai ya nahi
- Column numbers check karo (E=5, BB=54, CL=90)

**Image upload fail?**
- ImgBB API key verify karo

**Render deploy fail?**
- Logs dekho Render dashboard mein
- `requirements.txt` check karo
