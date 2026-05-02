"""
Phase 3 Demo — Payroll Calculation Engine
Runs full payroll for all 10 Kronos employees across US, UK, India, Australia.
No live Oracle or Kronos connection required.
Run with: python demo_phase3.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from dataclasses import dataclass, field
from typing import Optional

from adapters.kronos_adapter import MockKronosAdapter
from engine.payroll_engine import PayrollEngine, PayrollInput


# ── Inline mock country registry (Phase 1 data) ──────────────

@dataclass
class TaxBracket:
    tax_type: str; tax_name: str; employee_rate: float; employer_rate: float
    income_from: float; income_to: Optional[float]; applies_to: str

@dataclass
class CountryConfig:
    country_code: str; country_name: str; currency_code: str
    fiscal_year_start: str; pay_frequency: str
    tax_brackets: list = field(default_factory=list)
    def get(self, code): return self
    def calculate_period_divisor(self):
        return {"MONTHLY": 12, "BIWEEKLY": 26, "WEEKLY": 52}.get(self.pay_frequency, 12)

class MockRegistry:
    def __init__(self):
        self._countries = {
            "US": CountryConfig("US", "United States",  "USD", "01-01", "BIWEEKLY", [
                TaxBracket("INCOME", "Federal 10%",   0.10,  0,     0,      11600,  "ALL"),
                TaxBracket("INCOME", "Federal 12%",   0.12,  0,     11601,  47150,  "ALL"),
                TaxBracket("INCOME", "Federal 22%",   0.22,  0,     47151,  100525, "ALL"),
                TaxBracket("INCOME", "Federal 24%",   0.24,  0,     100526, 191950, "ALL"),
                TaxBracket("SOCIAL_SECURITY", "FICA", 0.062, 0.062, 0,      168600, "ALL"),
                TaxBracket("MEDICARE", "Medicare",    0.0145,0.0145,0,      None,   "ALL"),
            ]),
            "GB": CountryConfig("GB", "United Kingdom", "GBP", "04-06", "MONTHLY", [
                TaxBracket("INCOME", "Personal Allowance", 0.0,  0,    0,      12570,  "ALL"),
                TaxBracket("INCOME", "Basic Rate 20%",     0.20, 0,    12571,  50270,  "ALL"),
                TaxBracket("INCOME", "Higher Rate 40%",    0.40, 0,    50271,  125140, "ALL"),
                TaxBracket("NI",     "National Insurance", 0.08, 0.138,12570,  50270,  "ALL"),
            ]),
            "IN": CountryConfig("IN", "India", "INR", "04-01", "MONTHLY", [
                TaxBracket("INCOME", "0% Band",   0.0,  0,    0,       300000,  "ALL"),
                TaxBracket("INCOME", "5% Band",   0.05, 0,    300001,  600000,  "ALL"),
                TaxBracket("INCOME", "10% Band",  0.10, 0,    600001,  900000,  "ALL"),
                TaxBracket("INCOME", "20% Band",  0.20, 0,    900001,  1500000, "ALL"),
                TaxBracket("INCOME", "30% Band",  0.30, 0,    1500001, None,    "ALL"),
                TaxBracket("PF",     "Provident Fund", 0.12, 0.12, 0, None,    "FULLTIME"),
            ]),
            "AU": CountryConfig("AU", "Australia", "AUD", "07-01", "MONTHLY", [
                TaxBracket("INCOME", "0% Band",    0.0,   0, 0,      18200,  "ALL"),
                TaxBracket("INCOME", "19% Band",   0.19,  0, 18201,  45000,  "ALL"),
                TaxBracket("INCOME", "32.5% Band", 0.325, 0, 45001,  120000, "ALL"),
                TaxBracket("INCOME", "37% Band",   0.37,  0, 120001, 180000, "ALL"),
                TaxBracket("MEDICARE", "Medicare Levy", 0.02, 0, 0,  None,   "ALL"),
            ]),
        }
    def get(self, code): return self._countries[code.upper()]

# ── Employee configs (what Oracle would provide) ──────────────
EMPLOYEE_CONFIG = {
    "KRN001": {"country": "US", "currency": "USD", "type": "FULLTIME",  "salary": 95000, "rate": None,
               "deductions": [{"code": "401K",       "description": "401(k) 6%",        "percentage": 0.06, "pre_tax": True},
                               {"code": "HEALTH_INS", "description": "Health Insurance", "amount": 250,      "pre_tax": True}]},
    "KRN002": {"country": "IN", "currency": "INR", "type": "FULLTIME",  "salary": 1800000, "rate": None,
               "deductions": [{"code": "PF_INDIA", "description": "Provident Fund 12%", "percentage": 0.12, "pre_tax": True}]},
    "KRN003": {"country": "GB", "currency": "GBP", "type": "FULLTIME",  "salary": 65000, "rate": None,
               "deductions": [{"code": "PENSION_UK", "description": "Workplace Pension 5%", "percentage": 0.05, "pre_tax": True}]},
    "KRN004": {"country": "AU", "currency": "AUD", "type": "FULLTIME",  "salary": 95000, "rate": None,
               "deductions": [{"code": "SUPER_AU", "description": "Superannuation 11.5%", "percentage": 0.115, "pre_tax": False}]},
    "KRN005": {"country": "US", "currency": "USD", "type": "HOURLY",    "salary": None, "rate": 28.0,  "deductions": []},
    "KRN006": {"country": "IN", "currency": "INR", "type": "HOURLY",    "salary": None, "rate": 450.0, "deductions": []},
    "KRN007": {"country": "GB", "currency": "GBP", "type": "PARTTIME",  "salary": None, "rate": 18.0,  "deductions": []},
    "KRN008": {"country": "AU", "currency": "AUD", "type": "HOURLY",    "salary": None, "rate": 35.0,  "deductions": []},
    "KRN009": {"country": "US", "currency": "USD", "type": "FULLTIME",  "salary": 110000, "rate": None,
               "deductions": [{"code": "401K", "description": "401(k) 8%", "percentage": 0.08, "pre_tax": True}]},
    "KRN010": {"country": "IN", "currency": "INR", "type": "CONTRACT",  "salary": 2400000, "rate": None, "deductions": []},
}

PAY_PERIODS = {"BIWEEKLY": 26, "MONTHLY": 12, "WEEKLY": 52}
COUNTRY_FREQ = {"US": "BIWEEKLY", "GB": "MONTHLY", "IN": "MONTHLY", "AU": "MONTHLY"}

# ── Run payroll ───────────────────────────────────────────────
kronos   = MockKronosAdapter()
registry = MockRegistry()
engine   = PayrollEngine(registry)

period_start = date(2024, 11, 1)
period_end   = date(2024, 11, 30)

print("=" * 65)
print("  Global Payroll System — Phase 3 Demo")
print("  Payroll Calculation Engine")
print("=" * 65)
print(f"  Pay period: {period_start} → {period_end}\n")

results = []
for emp in kronos.get_all_employees():
    cfg     = EMPLOYEE_CONFIG[emp.kronos_id]
    tc      = kronos.get_timecard(emp.kronos_id, period_start, period_end)
    freq    = COUNTRY_FREQ[cfg["country"]]
    periods = PAY_PERIODS[freq]

    inp = PayrollInput(
        employee_id=int(emp.kronos_id.replace("KRN", "")),
        first_name=emp.first_name,
        last_name=emp.last_name,
        type_code=cfg["type"],
        country_code=cfg["country"],
        currency_code=cfg["currency"],
        base_salary=cfg["salary"],
        hourly_rate=cfg["rate"],
        regular_hours=tc.regular_hours,
        overtime_hours=tc.overtime_hours,
        pto_hours=tc.pto_hours,
        sick_hours=tc.sick_hours,
        pay_period_start=period_start,
        pay_period_end=period_end,
        pay_periods_per_year=periods,
        deductions=cfg["deductions"],
    )
    result = engine.calculate(inp)
    results.append(result)

# ── Summary table ─────────────────────────────────────────────
print(f"  {'Employee':<22} {'Type':<10} {'CCY':<4} {'Gross':>10} {'Tax':>10} {'Net':>10}")
print(f"  {'─'*22} {'─'*10} {'─'*4} {'─'*10} {'─'*10} {'─'*10}")
for r in results:
    print(f"  {r.employee_name:<22} {r.employee_type:<10} {r.currency_code:<4} "
          f"{r.gross_pay:>10,.2f} {r.total_employee_tax:>10,.2f} {r.net_pay:>10,.2f}")

# ── Detailed payslips for one employee per country ────────────
SHOWCASE = ["KRN001", "KRN003", "KRN002", "KRN004"]
showcase_results = [r for r in results if r.employee_id in [int(k.replace("KRN","")) for k in SHOWCASE]]

print("\n" + "=" * 65)
print("  DETAILED PAYSLIPS")
print("=" * 65)
for r in showcase_results:
    print(engine.format_payslip(r))

print(f"\n✅ Phase 3 complete! Payroll engine calculating across 4 countries.")
print(f"   Next: Phase 4 — PDF payslip generation\n")
