# 🌍 Kronos Oracle Global Payroll System

> An enterprise-grade, globally scalable payroll platform built on **Oracle DB**, **Kronos (UKG)**, and **FastAPI**. Supports full-time, hourly, part-time, and contracted employees across multiple countries, currencies, and tax jurisdictions.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Oracle](https://img.shields.io/badge/Oracle-DB-red?style=flat-square&logo=oracle)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?style=flat-square&logo=fastapi)
![Kronos](https://img.shields.io/badge/Kronos-UKG-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🎯 Core design principle

**Adding a new country = adding DB rows, not changing code.**

Every country's tax brackets, pay frequency, currency, statutory deductions, and leave entitlements are stored in Oracle. The payroll engine reads configs at runtime — when your company opens a new office in Singapore or Brazil, you insert the country config and tax rules, and the engine handles it automatically.

---

## 🌐 Countries supported

| Country | Currency | Pay Frequency | Tax System | Leave |
|---------|----------|---------------|------------|-------|
| 🇺🇸 United States | USD | Bi-weekly | Federal + FICA + Medicare | 15d PTO + 10d sick |
| 🇬🇧 United Kingdom | GBP | Monthly | Income Tax + NI | 28d annual + SSP |
| 🇮🇳 India | INR | Monthly | New Regime + PF + ESI | 21d earned + 12d sick |
| 🇦🇺 Australia | AUD | Monthly | Income Tax + Medicare Levy + Super | 20d annual + 10d personal |

---

## 👤 Employee types

| Type | Description | Payroll Logic |
|------|-------------|---------------|
| FULLTIME | Salaried, full benefits | Annual salary divided by pay periods |
| HOURLY | Hourly rate, overtime eligible | Hours x rate, 1.5x OT |
| PARTTIME | Part-time hourly | Hours x rate, no OT |
| CONTRACT | Fixed fee contractor | Fixed period fee |
| INTERN | Internship | Hourly, no benefits |

---

## 🏗️ Architecture

```
kronos-oracle-global-payroll-system/
├── adapters/
│   ├── kronos_adapter.py         # Kronos UKG mock + real API stub
│   ├── oracle_hr_adapter.py      # Oracle HR read/write + Kronos sync
│   └── fx_adapter.py             # Live FX rates (frankfurter.app)
├── core/
│   └── country_registry.py       # Country config loader from Oracle
├── engine/
│   ├── payroll_engine.py         # Gross to tax to deductions to net
│   ├── pdf_generator.py          # Professional PDF payslips
│   ├── leave_tracker.py          # Leave balances, requests, approvals
│   └── bonus_deduction_engine.py # Bonuses, deductions, performance pay
├── api/
│   ├── app.py                    # FastAPI app
│   ├── auth.py                   # JWT auth + role-based access
│   └── routers/                  # Auth, employees, payroll endpoints
├── portal/
│   └── index.html                # Employee self-service portal
├── db/
│   ├── migrations/               # Oracle DDL (13 tables)
│   ├── seeds/                    # Country data + tax rules
│   └── run_migrations.py         # Schema runner CLI
├── demo_phase1.py                # Country config demo
├── demo_phase2.py                # Kronos + FX demo
├── demo_phase3.py                # Payroll engine demo
├── demo_phase4.py                # PDF payslip demo
├── demo_phase7.py                # Leave + bonus demo
└── requirements.txt
```

---

## 🚀 Quick start

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Run any demo (no Oracle or Kronos needed)**
```bash
python demo_phase1.py   # Country config + tax brackets
python demo_phase2.py   # Kronos timecards + FX rates
python demo_phase3.py   # Full payroll calculations
python demo_phase4.py   # PDF payslip generation
python demo_phase7.py   # Leave tracker + bonuses
```

**3. Open the employee portal**
```
Open portal/index.html in your browser
Login: admin@acme.com / admin123
```

**4. Start the API**
```bash
uvicorn api.app:app --reload
# Docs: http://localhost:8000/docs
```

**5. Apply Oracle schema**
```bash
python db/run_migrations.py \
  --host localhost --service ORCL \
  --user hr --password secret --seeds
```

---

## 📡 API endpoints

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| POST | /auth/login | Public | Get JWT token |
| GET | /auth/me | Any | Current user info |
| GET | /employees/ | Admin/Manager | List all employees |
| GET | /employees/{id} | Any | Get employee (own only for employees) |
| POST | /payroll/run | Admin | Trigger payroll run |
| GET | /payroll/payslips/{id} | Any | Get payslip data |
| GET | /payroll/payslips/{id}/pdf | Any | Download payslip PDF |

**Demo credentials:**

| Email | Password | Role |
|-------|----------|------|
| admin@acme.com | admin123 | ADMIN |
| manager@acme.com | manager123 | MANAGER |
| jcarter@acme.com | emp123 | EMPLOYEE |

---

## 🔌 Kronos integration

Swap MockKronosAdapter for RealKronosAdapter with your UKG credentials — no other code changes needed:

```python
from adapters.kronos_adapter import RealKronosAdapter

adapter = RealKronosAdapter(
    base_url="https://your-tenant.kronos.net",
    client_id="your-client-id",
    client_secret="your-secret",
    tenant_id="your-tenant-id",
)
```

---

## 🗺️ Build roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Complete | Oracle schema + country config registry |
| 2 | Complete | Kronos adapter + Oracle HR adapter + FX rates |
| 3 | Complete | Payroll calculation engine |
| 4 | Complete | PDF payslip generation |
| 5 | Complete | FastAPI layer + JWT auth + role-based access |
| 6 | Complete | Employee self-service portal |
| 7 | Complete | Leave tracker + bonus and deductions engine |
| 8 | Complete | Demo data + documentation |

---

## 🛠️ Tech stack

| Layer | Technology |
|-------|-----------|
| Time & attendance | Kronos UKG (mock adapter, real API ready) |
| HR & payroll data | Oracle DB via python-oracledb |
| Calculation engine | Python pure business logic |
| PDF payslips | reportlab |
| FX rates | frankfurter.app (free, no key needed) |
| REST API | FastAPI + JWT auth |
| Employee portal | Vanilla JS + HTML (no build step) |

---

## 📄 License

MIT
