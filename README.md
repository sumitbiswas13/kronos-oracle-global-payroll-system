# 🌍 Global Payroll System

> An enterprise-grade, globally scalable payroll platform built on Oracle DB + FastAPI + Kronos (UKG). Supports full-time, hourly, part-time, and contracted employees across multiple countries, currencies, and tax jurisdictions.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Oracle](https://img.shields.io/badge/Oracle-DB-red?style=flat-square&logo=oracle)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?style=flat-square&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Key design principle

**Adding a new country = adding DB rows, not changing code.**

Every country's tax brackets, pay frequency, currency, and fiscal year are stored in Oracle. The payroll engine reads configs at runtime — when your company opens a new office in Singapore or Brazil, you insert the country config and tax rules, and the engine handles it automatically.

---

## 🌐 Countries supported (Phase 1)

| Country | Currency | Pay Frequency | Tax System |
|---------|----------|---------------|------------|
| United States | USD | Bi-weekly | Federal + FICA + Medicare |
| United Kingdom | GBP | Monthly | Income Tax + NI |
| India | INR | Monthly | New Regime + PF |
| Australia | AUD | Monthly | Income Tax + Medicare Levy + Super |

---

## 👤 Employee types

- `FULLTIME` — salaried, full benefits
- `HOURLY` — paid from Kronos hours, overtime eligible
- `PARTTIME` — prorated salary or hourly
- `CONTRACT` — fixed fee, jurisdiction-specific rules
- `INTERN` — internship, configurable pay

---

## 🗂️ Project structure

```
global-payroll-system/
├── db/
│   ├── migrations/
│   │   └── 001_initial_schema.sql    # All Oracle tables
│   ├── seeds/
│   │   ├── 001_seed_data.sql         # Countries, employee types, leave types
│   │   └── 002_tax_rules.sql         # Tax brackets for US, GB, IN, AU
│   └── run_migrations.py             # Schema runner CLI
├── core/
│   └── country_registry.py           # Country config loader + cache
├── demo_phase1.py                    # Phase 1 demo (no Oracle needed)
└── README.md
```

---

## 🚀 Quick start

**Run the demo (no Oracle needed)**
```bash
python demo_phase1.py
```

**Apply schema to Oracle**
```bash
python db/run_migrations.py \
  --host localhost --service ORCL \
  --user hr --password secret \
  --seeds
```

---

## 🗺️ Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Oracle schema + country config registry |
| 2 | 🔜 Next | Kronos adapter + Oracle HR adapter |
| 3 | 📋 Planned | Payroll calculation engine |
| 4 | 📋 Planned | FX rates + multi-currency payslip PDF |
| 5 | 📋 Planned | FastAPI layer + JWT auth |
| 6 | 📋 Planned | React employee self-service portal |
| 7 | 📋 Planned | Leave tracker + bonus/deduction engine |

---

## 📄 License

MIT
