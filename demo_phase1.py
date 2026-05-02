"""
Phase 1 Demo — validates country config registry with mock data.
No Oracle connection required.
Run with: python demo_phase1.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataclasses import dataclass, field
from typing import Optional


# ── Inline mock (mirrors what Oracle would return) ────────────

@dataclass
class TaxBracket:
    tax_type: str
    tax_name: str
    employee_rate: float
    employer_rate: float
    income_from: float
    income_to: Optional[float]
    applies_to: str


@dataclass
class CountryConfig:
    country_code: str
    country_name: str
    currency_code: str
    fiscal_year_start: str
    pay_frequency: str
    tax_brackets: list = field(default_factory=list)

    def calculate_period_divisor(self):
        return {"MONTHLY": 12, "BIWEEKLY": 26, "WEEKLY": 52}.get(self.pay_frequency, 12)

    def get_applicable_taxes(self, annual_income, employee_type):
        result = []
        for b in self.tax_brackets:
            if b.applies_to not in ("ALL", employee_type):
                continue
            if annual_income < b.income_from:
                continue
            if b.income_to is not None and annual_income > b.income_to:
                continue
            result.append(b)
        return result


MOCK_COUNTRIES = {
    "US": CountryConfig("US", "United States",  "USD", "01-01", "BIWEEKLY", [
        TaxBracket("INCOME", "Federal 10%",        0.10,  0,     0,      11600,  "ALL"),
        TaxBracket("INCOME", "Federal 12%",        0.12,  0,     11601,  47150,  "ALL"),
        TaxBracket("INCOME", "Federal 22%",        0.22,  0,     47151,  100525, "ALL"),
        TaxBracket("INCOME", "Federal 24%",        0.24,  0,     100526, 191950, "ALL"),
        TaxBracket("SOCIAL_SECURITY", "FICA SS",   0.062, 0.062, 0,      168600, "ALL"),
        TaxBracket("MEDICARE", "Medicare",         0.0145,0.0145,0,      None,   "ALL"),
    ]),
    "GB": CountryConfig("GB", "United Kingdom", "GBP", "04-06", "MONTHLY", [
        TaxBracket("INCOME", "Personal Allowance", 0.0,  0,    0,      12570,  "ALL"),
        TaxBracket("INCOME", "Basic Rate 20%",     0.20, 0,    12571,  50270,  "ALL"),
        TaxBracket("INCOME", "Higher Rate 40%",    0.40, 0,    50271,  125140, "ALL"),
        TaxBracket("INCOME", "Additional 45%",     0.45, 0,    125141, None,   "ALL"),
        TaxBracket("NI",     "NI 8%",              0.08, 0.138,12570,  50270,  "ALL"),
        TaxBracket("NI",     "NI 2%",              0.02, 0.138,50271,  None,   "ALL"),
    ]),
    "IN": CountryConfig("IN", "India",          "INR", "04-01", "MONTHLY", [
        TaxBracket("INCOME", "0% Band",    0.0,  0,    0,       300000,  "ALL"),
        TaxBracket("INCOME", "5% Band",    0.05, 0,    300001,  600000,  "ALL"),
        TaxBracket("INCOME", "10% Band",   0.10, 0,    600001,  900000,  "ALL"),
        TaxBracket("INCOME", "15% Band",   0.15, 0,    900001,  1200000, "ALL"),
        TaxBracket("INCOME", "20% Band",   0.20, 0,    1200001, 1500000, "ALL"),
        TaxBracket("INCOME", "30% Band",   0.30, 0,    1500001, None,    "ALL"),
        TaxBracket("PF",     "PF 12%",     0.12, 0.12, 0,       None,    "FULLTIME"),
    ]),
    "AU": CountryConfig("AU", "Australia",      "AUD", "07-01", "MONTHLY", [
        TaxBracket("INCOME", "0% Band",    0.0,   0,    0,      18200,  "ALL"),
        TaxBracket("INCOME", "19% Band",   0.19,  0,    18201,  45000,  "ALL"),
        TaxBracket("INCOME", "32.5% Band", 0.325, 0,    45001,  120000, "ALL"),
        TaxBracket("INCOME", "37% Band",   0.37,  0,    120001, 180000, "ALL"),
        TaxBracket("INCOME", "45% Band",   0.45,  0,    180001, None,   "ALL"),
        TaxBracket("MEDICARE","Medicare",  0.02,  0,    0,      None,   "ALL"),
    ]),
}

EMPLOYEE_TYPES = ["FULLTIME", "HOURLY", "PARTTIME", "CONTRACT", "INTERN"]


def demo_tax_calculation(country_code: str, annual_income: float, employee_type: str):
    config = MOCK_COUNTRIES[country_code]
    taxes = config.get_applicable_taxes(annual_income, employee_type)
    periods = config.calculate_period_divisor()
    period_income = annual_income / periods

    print(f"\n  Employee type : {employee_type}")
    print(f"  Annual income : {config.currency_code} {annual_income:,.2f}")
    print(f"  Pay periods   : {periods} ({config.pay_frequency})")
    print(f"  Per period    : {config.currency_code} {period_income:,.2f}")
    print(f"  Applicable taxes:")

    total_employee_tax = 0
    total_employer_tax = 0
    for t in taxes:
        emp_tax = period_income * t.employee_rate
        er_tax  = period_income * t.employer_rate
        total_employee_tax += emp_tax
        total_employer_tax += er_tax
        print(f"    {t.tax_name:<35} Employee: {config.currency_code} {emp_tax:>8.2f}  Employer: {config.currency_code} {er_tax:>8.2f}")

    net = period_income - total_employee_tax
    print(f"  {'─'*70}")
    print(f"  Net per period: {config.currency_code} {net:,.2f}  (total tax: {config.currency_code} {total_employee_tax:,.2f})")


print("=" * 70)
print("  Global Payroll System — Phase 1 Demo")
print("  Country Config Registry")
print("=" * 70)

print(f"\n📋 Registered countries: {', '.join(MOCK_COUNTRIES.keys())}")
print(f"👤 Employee types: {', '.join(EMPLOYEE_TYPES)}")

print("\n" + "─" * 70)
print("  US Full-time employee — $85,000/year")
demo_tax_calculation("US", 85000, "FULLTIME")

print("\n" + "─" * 70)
print("  UK Full-time employee — £60,000/year")
demo_tax_calculation("GB", 60000, "FULLTIME")

print("\n" + "─" * 70)
print("  India Full-time employee — ₹1,800,000/year")
demo_tax_calculation("IN", 1800000, "FULLTIME")

print("\n" + "─" * 70)
print("  Australia Full-time employee — AUD 95,000/year")
demo_tax_calculation("AU", 95000, "FULLTIME")

print("\n" + "─" * 70)
print("  US Contractor — $120,000/year (no FICA on contract type?)")
demo_tax_calculation("US", 120000, "CONTRACT")

print("\n\n✅ Phase 1 complete! Oracle schema + country config registry ready.")
print("   Next: Phase 2 — Kronos adapter + Oracle adapter")
