# ScholarPilot AI | Your AI-Powered Scholarship Advisor

The Autonomous Scholarship Intelligence Platform that automatically monitors global accredited scholarships, computes applicant admission odds, drafts institutional dossiers, and delivers weekly personalized digests directly to student inboxes.

[![FastAPI](https://img.shields.io/badge/FastAPI-Production%20Ready-009688?style=flat-square&logo=fastapi&logoColor=white)](web/app.py)
[![Google Gemini API](https://img.shields.io/badge/Google%20Gemini-3.5%20Flash%20Lite-2563eb?style=flat-square&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Render](https://img.shields.io/badge/Render-Deploy%20Ready-46e3b7?style=flat-square&logo=render&logoColor=black)](render.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-slate?style=flat-square)](LICENSE)

---

## Executive Overview

ScholarPilot AI is a production-grade, 100% autonomous scholarship platform built to democratize higher education opportunities for ambitious international students, with special priority allocation for students in Palestine and emerging regions.

Students register their academic profile once (degree, GPA, major, extracurriculars, and country of residence). The autonomous background engine handles the rest without human intervention:

1. **Autonomous Live Ingestion & Verification**: Periodically monitors, parses, and validates flagship global opportunities (DAAD, Chevening, Fulbright, Stipendium Hungaricum, Turkiye Burslari, Lester B. Pearson, GKS).
2. **Predictive Admission Probability & Match Scoring**: Computes admission odds based on GPA benchmarks, leadership activities, hackathons, and country quotas.
3. **Automated Weekly Email Digests**: Automatically prepares and dispatches comprehensive weekly scholarship reports with official application links and deadlines.
4. **Deadline Countdown Reminders**: Monitored deadlines automatically trigger alert notifications at 30, 14, 7, and 2-day milestones.
5. **Interactive AI Academic Advisor**: Conversational advisor model answering student queries concisely with zero fluff.
6. **Smart Institutional Application Dossier Studio**: Instantly drafts Statement of Purpose / Motivation Letters, Academic CVs, Professor Recommendation templates, and Verification Checklists formatted with official letterheads.

---

## Architecture & Directory Layout

```text
scholarship-automation/
├── data/
│   ├── live_scholarships.json       # Live synced roster of verified global opportunities
│   ├── subscribers.json             # Student registry, tracking preferences, and match profiles
│   └── users.json                   # Authenticated student records (Argon2 / SHA-256 + salt)
├── services/
│   ├── advisor_service.py           # Gemini AI consultation, admission odds, and document architecture
│   ├── auth_service.py              # Strict student authentication, registration, and credential hashing
│   ├── automation_service.py        # Background daemon handling automated email dispatches & deadlines
│   ├── scholarship_engine.py        # HTML / CSV report compiler and SMTP delivery engine
│   ├── security_utils.py            # Strict input validation filters (GPA numeric regex, XSS sanitization)
│   └── subscriber_service.py        # Subscriber management and watchlist tracking
├── web/
│   ├── static/
│   │   └── css/
│   │       └── scholarpilot.css     # Production SaaS design system tokens, themes, and animations
│   ├── templates/
│   │   ├── dashboard.html           # Authenticated student workspace, metrics, and watchlist
│   │   └── index.html               # Public landing page, card swiper, AI advisor, and document studio
│   └── app.py                       # FastAPI application, REST endpoints, and security middleware
├── tests/
│   └── test_automation_suite.py     # End-to-end integration and security test suite
├── render.yaml                      # One-click Render infrastructure deployment spec
├── Dockerfile                       # Containerized production runtime
├── requirements.txt                 # Python dependencies
└── README.md                        # Documentation and architecture guide
```

---

## Design System & UX Standards

The ScholarPilot AI interface adheres to high-end SaaS product design principles (Linear, Stripe, Vercel, Revolut):

* **Color Palette**: Clean white surfaces and soft slate canvas in Light Mode; deep neutral charcoal in Dark Mode with zero diffuse glow or garish gradients.
* **Typography**: Clean scale pairing `Inter` and `Plus Jakarta Sans` for Latin numerals with `Tajawal` and `Cairo` for legible Arabic presentation.
* **Iconography**: 100% SVG icon system powered by Lucide. Zero emojis across navigation, buttons, forms, alerts, headers, cards, or emails.
* **Accessibility**: Strict WCAG AA compliance with visible `:focus-visible` rings, high contrast ratios, and semantic HTML elements.
* **States**: Explicit skeleton loaders during API latency, empty state illustrations, and interactive feedback.

---

## Local Setup & Development

### 1. Prerequisites
* Python 3.10+
* Google Gemini API Key (optional for mock fallback, recommended for live AI responses)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/medozaiter/scholarship-automation.git
cd scholarship-automation

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

### 3. Execution
```bash
uvicorn web.app:app --host 0.0.0.0 --port 7860 --reload
```
Navigate to `http://localhost:7860` to access the platform.

### 4. Running Verification Test Suite
```bash
python tests/test_automation_suite.py
```

---

## Security & Verification

* **Input Sanitization**: Strict regex whitelisting for numeric GPA fields, character limits, and text sanitizers preventing XSS and script injection.
* **Authentication**: Salted SHA-256 password hashing with dedicated student session management.
* **Headers**: Production security middleware injecting `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and strict referrer policies.

---

## License

This project is licensed under the MIT License - open and accessible to empower students worldwide.

Developed and maintained by [Mustafa AbuZaiter](https://github.com/medozaiter).
