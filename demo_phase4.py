"""
Phase 4 Demo — PDF Payslip Generation
Generates professional PDF payslips for all 10 employees.
Run with: python demo_phase4.py
Output: output/payslips/*.pdf
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from dataclasses import dataclass, field
from typing import Optional

from adapters.kronos_adapter import MockKronosAdapter
from engine.payroll_engine import PayrollEngine, PayrollInput
from engine.pdf_generator import PayslipPDFGenerator


# ── Reuse mock registry from Phase 3 ─────────────────────────
@dataclass
class TaxBracket:
    tax_type: str; tax_name: str; employee_rate: float; employer_rate: float
    income_from: float; income_to: Optional[float]; applies_to: str

@dataclass
class CountryConfig:
    country_code: str; country_name: str; currency_code: str
    fiscal_year_start: str; pay_frequency: str
    tax_brackets: list = field(default_factory=list)
    def calculate_period_divisor(self):
        return {"MONTHLY": 12, "BIWEEKLY": 26, "WEEKLY": 52}.get(self.pay_frequency, 12)

class MockRegistry:
    def __init__(self):
        self._c = {
            "US": CountryConfig("US","United States","USD","01-01","BIWEEKLY",[
                TaxBracket("INCOME","Federal 10%",   0.10,  0,      0,      11600,  "ALL"),
                TaxBracket("INCOME","Federal 12%",   0.12,  0,      11601,  47150,  "ALL"),
                TaxBracket("INCOME","Federal 22%",   0.22,  0,      47151,  100525, "ALL"),
                TaxBracket("INCOME","Federal 24%",   0.24,  0,      100526, 191950, "ALL"),
                TaxBracket("SOCIAL_SECURITY","FICA", 0.062, 0.062,  0,      168600, "ALL"),
                TaxBracket("MEDICARE","Medicare",    0.0145,0.0145, 0,      None,   "ALL"),
            ]),
            "GB": CountryConfig("GB","United Kingdom","GBP","04-06","MONTHLY",[
                TaxBracket("INCOME","Personal Allowance",0.0, 0, 0,     12570, "ALL"),
                TaxBracket("INCOME","Basic Rate 20%",   0.20, 0, 12571, 50270, "ALL"),
                TaxBracket("INCOME","Higher Rate 40%",  0.40, 0, 50271, 125140,"ALL"),
                TaxBracket("NI","National Insurance",   0.08, 0.138, 12570, 50270,"ALL"),
            ]),
            "IN": CountryConfig("IN","India","INR","04-01","MONTHLY",[
                TaxBracket("INCOME","0% Band",  0.0,  0, 0,       300000,  "ALL"),
                TaxBracket("INCOME","5% Band",  0.05, 0, 300001,  600000,  "ALL"),
                TaxBracket("INCOME","10% Band", 0.10, 0, 600001,  900000,  "ALL"),
                TaxBracket("INCOME","20% Band", 0.20, 0, 900001,  1500000, "ALL"),
                TaxBracket("INCOME","30% Band", 0.30, 0, 1500001, None,    "ALL"),
                TaxBracket("PF","Provident Fund", 0.12, 0.12, 0,  None,    "FULLTIME"),
            ]),
            "AU": CountryConfig("AU","Australia","AUD","07-01","MONTHLY",[
                TaxBracket("INCOME","0% Band",    0.0,   0, 0,      18200,  "ALL"),
                TaxBracket("INCOME","19% Band",   0.19,  0, 18201,  45000,  "ALL"),
                TaxBracket("INCOME","32.5% Band", 0.325, 0, 45001,  120000, "ALL"),
                TaxBracket("INCOME","37% Band",   0.37,  0, 120001, 180000, "ALL"),
                TaxBracket("MEDICARE","Medicare", 0.02,  0, 0,      None,   "ALL"),
            ]),
        }
    def get(self, code): return self._c[code.upper()]

EMPLOYEE_CONFIG = {
    "KRN001": {"country":"US","currency":"USD","type":"FULLTIME", "salary":95000,  "rate":None,
               "deductions":[{"code":"401K","description":"401(k) 6%","percentage":0.06,"pre_tax":True},
                              {"code":"HEALTH","description":"Health Insurance","amount":250,"pre_tax":True}]},
    "KRN002": {"country":"IN","currency":"INR","type":"FULLTIME", "salary":1800000,"rate":None,
               "deductions":[{"code":"PF","description":"Provident Fund 12%","percentage":0.12,"pre_tax":True}]},
    "KRN003": {"country":"GB","currency":"GBP","type":"FULLTIME", "salary":65000,  "rate":None,
               "deductions":[{"code":"PENSION","description":"Workplace Pension 5%","percentage":0.05,"pre_tax":True}]},
    "KRN004": {"country":"AU","currency":"AUD","type":"FULLTIME", "salary":95000,  "rate":None,
               "deductions":[{"code":"SUPER","description":"Superannuation 11.5%","percentage":0.115,"pre_tax":False}]},
    "KRN005": {"country":"US","currency":"USD","type":"HOURLY",   "salary":None,   "rate":28.0,  "deductions":[]},
    "KRN006": {"country":"IN","currency":"INR","type":"HOURLY",   "salary":None,   "rate":450.0, "deductions":[]},
    "KRN007": {"country":"GB","currency":"GBP","type":"PARTTIME", "salary":None,   "rate":18.0,  "deductions":[]},
    "KRN008": {"country":"AU","currency":"AUD","type":"HOURLY",   "salary":None,   "rate":35.0,  "deductions":[]},
    "KRN009": {"country":"US","currency":"USD","type":"FULLTIME", "salary":110000, "rate":None,
               "deductions":[{"code":"401K","description":"401(k) 8%","percentage":0.08,"pre_tax":True}]},
    "KRN010": {"country":"IN","currency":"INR","type":"CONTRACT", "salary":2400000,"rate":None,  "deductions":[]},
}
PAY_PERIODS  = {"BIWEEKLY":26,"MONTHLY":12,"WEEKLY":52}
COUNTRY_FREQ = {"US":"BIWEEKLY","GB":"MONTHLY","IN":"MONTHLY","AU":"MONTHLY"}

period_start = date(2024, 11, 1)
period_end   = date(2024, 11, 30)

kronos   = MockKronosAdapter()
registry = MockRegistry()
engine   = PayrollEngine(registry)
pdf_gen  = PayslipPDFGenerator(output_dir="output/payslips")

print("=" * 60)
print("  Global Payroll System — Phase 4 Demo")
print("  PDF Payslip Generation")
print("=" * 60)
print(f"\n  Pay period: {period_start} → {period_end}")
print(f"  Generating payslips for {len(EMPLOYEE_CONFIG)} employees...\n")

results = []
for emp in kronos.get_all_employees():
    cfg     = EMPLOYEE_CONFIG[emp.kronos_id]
    tc      = kronos.get_timecard(emp.kronos_id, period_start, period_end)
    freq    = COUNTRY_FREQ[cfg["country"]]
    periods = PAY_PERIODS[freq]

    inp = PayrollInput(
        employee_id=int(emp.kronos_id.replace("KRN","")),
        first_name=emp.first_name, last_name=emp.last_name,
        type_code=cfg["type"], country_code=cfg["country"],
        currency_code=cfg["currency"], base_salary=cfg["salary"],
        hourly_rate=cfg["rate"], regular_hours=tc.regular_hours,
        overtime_hours=tc.overtime_hours, pto_hours=tc.pto_hours,
        sick_hours=tc.sick_hours, pay_period_start=period_start,
        pay_period_end=period_end, pay_periods_per_year=periods,
        deductions=cfg["deductions"],
    )
    results.append(engine.calculate(inp))

paths = pdf_gen.generate_batch(results, company_name="Acme Global Corp")

print(f"\n  {len(paths)} payslips generated in output/payslips/")
print(f"\n✅ Phase 4 complete! PDF payslips ready.")
print(f"   Next: Phase 5 — FastAPI layer + JWT auth\n")
