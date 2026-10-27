# 🎓 Enterprise Scholarship Finder & Advisory Platform (Telegram Bot)

A production-grade, asynchronous Telegram Bot powered by **`python-telegram-bot` (v20+ async)**, an asynchronous **SQLite database (`aiosqlite`)**, and the official **`google-genai` SDK for Google Gemini**.

Engineered specifically to solve scholarship search challenges for students (especially international and Palestinian students), featuring **strict URL verification (zero hallucinations)**, **sub-second database caching**, **automated 24-hour background crawlers**, **custom scholarship alerts**, **academic eligibility scoring**, and a **complete application toolkit**.

---

## 🌟 Advanced Features & Upgrades

### 1. ⚡ Database Caching & Fast Indexing (Instant Retrieval)
- Instead of waiting 15–20 seconds on every search, queries are cached in an asynchronous SQLite database (`aiosqlite`).
- **Sub-Second Results**: Repeated searches for the same degree, major, and country return instantly (`< 1s`), drastically reducing API consumption.
- Configurable **Time-To-Live (TTL)** (default: 24 hours).

### 2. 🛡️ Strict URL Verification & Mandatory Date Advisory
- **Zero URL Hallucination**: Gemini is constrained to take URLs verbatim exclusively from verified search engine sources (`Exact URL`).
- **Mandatory User Advisory Notice**: Appends a clear advisory banner to each scholarship card:
  > ⚠️ *ملاحظة: يرجى التأكد من تاريخ الإغلاق والشروط النهائية عبر الرابط الرسمي دائماً.*
- **Strict Cycle Filtering**: Eliminates expired opportunities, focusing exclusively on programs open now or opening in the upcoming weeks/months.

### 3. 🔔 Personalized Scholarship Push Alerts
- Students can click `[ 🔔 نبهني فور توفر منح جديدة في هذا التخصص ]` after any search.
- When the automated background crawler discovers a new matching scholarship, it dispatches an instant push notification directly to the student's Telegram chat.

### 4. 📊 Initial Eligibility Checker (`/check`)
- Compares a student's profile (GPA, English proficiency/IELTS, age/graduation year) against historical competitive benchmarks of major international programs (e.g., Turkiye Burslari, Stipendium Hungaricum, MEPI, Toronto Pearson, UBC, GKS).
- Produces:
  - **Compatibility Score** (e.g., *85% - High competitive probability*).
  - **Academic Strengths**.
  - **Weaknesses / Missing Requirements** (e.g., missing accredited English test, age cutoffs).
  - **Concrete 3-Step Action Plan**.

### 5. 🧰 Application Toolkit (`/toolkit`)
Built-in library providing:
- **Field-Specific Motivation Letters (SOPs)**: Ready-to-use templates tailored for Cybersecurity, Software Engineering, and Artificial Intelligence.
- **Academic CV Guide**: Clear instructions for European **Europass** format vs. North American (US/Canada) resume rules.
- **Letter of Recommendation (LOR) Guide**: Professional email request templates to professors and employers.

### 6. 📢 Urgent Scholarships Channel Broadcasting
- Automatically posts urgent or newly discovered fully funded scholarships with approaching deadlines directly to a public Telegram channel (`TELEGRAM_CHANNEL_ID`).
- Each broadcast includes a direct button leading back to the bot for full details and application instructions.

### 7. 🔌 Pluggable Search Providers
- Supports **Tavily Search API** (`TAVILY_API_KEY`) for high-speed, structured results.
- Seamlessly falls back to **DuckDuckGo Search** with multi-query execution if no API key is supplied.

---

## 📁 Project Architecture

```
Scholarship/
├── main.py                     # Bot entrypoint, JobQueue scheduler & database startup
├── database.py                 # Async SQLite manager (aiosqlite) for cache & subscriptions
├── handlers/
│   ├── __init__.py
│   ├── conversation.py         # Multi-step state machine with instant DB cache lookup
│   ├── eligibility.py          # AI Academic Eligibility Checker flow (/check)
│   └── toolkit.py              # Application Toolkit (Motivation letters, CV, LORs) (/toolkit)
├── services/
│   ├── __init__.py
│   ├── search_service.py       # Multi-engine search (Tavily / DuckDuckGo fallback)
│   ├── gemini_service.py       # Strict extraction, zero-hallucination verification & evaluation
│   └── broadcast_service.py    # 24-Hour crawler, subscriber alert dispatcher & channel poster
├── requirements.txt            # Project dependencies
├── .env.example                # Sample environment configuration
├── .gitignore                  # Git ignore rules
└── README.md                   # Full documentation & setup guide
```

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- **Python 3.10+** installed.
- **Telegram Bot Token**: Created via [@BotFather](https://t.me/BotFather).
- **Google Gemini API Key**: Created at [Google AI Studio](https://aistudio.google.com/).

### 2. Setup Virtual Environment & Install Dependencies

```bash
cd Scholarship

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
.\venv\Scripts\activate.bat

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure `.env`

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Fill in your configuration:

```ini
# Required
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
GEMINI_API_KEY=AIzaSyD-YourOfficialGeminiKeyHere
GEMINI_MODEL=gemini-3.8-flash

# Optional: Public Channel Broadcasting (e.g. @MyScholarshipsChannel)
TELEGRAM_CHANNEL_ID=

# Optional: Official High-Speed Search API (Leave blank to use DuckDuckGo)
TAVILY_API_KEY=

# Cache TTL in hours
CACHE_TTL_HOURS=24
```

### 4. Run the Bot

```bash
python main.py
```

---

## 🤖 Bot Commands & Usage

| Command | Description |
|---|---|
| `/start` | Launches the interactive multi-select scholarship discovery wizard |
| `/check` | Runs the AI Academic Eligibility & Profile Compatibility Checker |
| `/toolkit` | Opens the Application Toolkit (Motivation Letters, CVs, LOR templates) |
| `/help` | Displays command reference and bot overview |
| `/cancel` | Resets current flow and returns to start |

---

## ☁️ 24/7 Cloud Deployment

### Deployment on Render (Background Worker)
1. Push your repository to GitHub.
2. In [Render](https://render.com/), create a **New Background Worker**.
3. Select your repository.
4. Set:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. Under **Environment Variables**, add `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, etc.
6. Click **Deploy**.

### Deployment on Railway
1. Create a **New Project** in [Railway](https://railway.app/) and select your GitHub repo.
2. Add your `.env` variables under **Variables**.
3. Set the deploy start command to `python main.py`.
4. Railway will automatically keep the bot and the 24-hour background crawler active 24/7.
