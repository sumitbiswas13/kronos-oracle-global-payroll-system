"""
Payroll Calculation Engine
The heart of the system — calculates gross pay, taxes, deductions and net pay
for every employee type across every country. Pure Python, no DB dependencies.
All inputs come from adapters; all outputs go to Oracle via the payroll runner.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import date


# ── Input / Output models ─────────────────────────────────────

@dataclass
class PayrollInput:
    employee_id: int
    first_name: str
    last_name: str
    type_code: str              # FULLTIME | HOURLY | PARTTIME | CONTRACT | INTERN
    country_code: str
    currency_code: str
    base_salary: Optional[float]    # Annual, for salaried employees
    hourly_rate: Optional[float]    # For hourly/part-time
    regular_hours: float            # From Kronos
    overtime_hours: float           # From Kronos
    pto_hours: float                # Paid time off (already in regular)
    sick_hours: float               # Sick leave
    pay_period_start: date
    pay_period_end: date
    pay_periods_per_year: int       # 12 | 26 | 52
    deductions: list[dict] = field(default_factory=list)  # [{code, amount, pct, pre_tax}]
    bonuses: list[dict] = field(default_factory=list)     # [{description, amount}]
    overtime_multiplier: float = 1.5


@dataclass
class TaxLine:
    description: str
    tax_type: str
    employee_amount: float
    employer_amount: float
    rate: float


@dataclass
class DeductionLine:
    description: str
    amount: float
    is_pre_tax: bool


@dataclass
class EarningLine:
    description: str
    amount: float
    hours: Optional[float] = None


@dataclass
class PayrollResult:
    employee_id: int
    employee_name: str
    pay_period_start: date
    pay_period_end: date
    currency_code: str
    country_code: str
    employee_type: str

    # Earnings
    earnings: list[EarningLine] = field(default_factory=list)
    gross_pay: float = 0.0

    # Pre-tax deductions (reduce taxable income)
    pre_tax_deductions: list[DeductionLine] = field(default_factory=list)
    total_pre_tax_deductions: float = 0.0

    # Taxable income
    taxable_income: float = 0.0

    # Taxes
    taxes: list[TaxLine] = field(default_factory=list)
    total_employee_tax: float = 0.0
    total_employer_tax: float = 0.0

    # Post-tax deductions
    post_tax_deductions: list[DeductionLine] = field(default_factory=list)
    total_post_tax_deductions: float = 0.0

    # Net
    net_pay: float = 0.0

    # Hours summary
    regular_hours: float = 0.0
    overtime_hours: float = 0.0
    total_hours: float = 0.0


# ── Tax calculator ────────────────────────────────────────────

class TaxCalculator:
    """
    Calculates taxes using progressive brackets loaded from country config.
    Handles annualised income → per-period tax correctly.
    """

    def calculate(
        self,
        taxable_income_period: float,
        pay_periods: int,
        tax_brackets: list,
        employee_type: str,
    ) -> list[TaxLine]:
        """
        Annualise the period income, apply brackets, return per-period tax lines.
        This is the correct way to handle progressive tax — never apply brackets
        to a single period's income directly.
        """
        annual_income = taxable_income_period * pay_periods
        tax_lines = []
        seen_types = set()

        for bracket in tax_brackets:
            # Filter by employee type
            if bracket.applies_to not in ("ALL", employee_type):
                continue

            # Check income falls within this bracket
            if annual_income <= bracket.income_from:
                continue
            if bracket.income_to is not None and annual_income > bracket.income_to:
                continue

            # Calculate tax on the income within this bracket
            band_from = bracket.income_from
            band_to   = bracket.income_to if bracket.income_to else annual_income
            taxable_in_band = min(annual_income, band_to) - band_from
            taxable_in_band = max(0.0, taxable_in_band)

            annual_employee_tax = taxable_in_band * bracket.employee_rate
            annual_employer_tax = taxable_in_band * bracket.employer_rate

            period_employee_tax = round(annual_employee_tax / pay_periods, 2)
            period_employer_tax = round(annual_employer_tax / pay_periods, 2)

            if period_employee_tax == 0 and period_employer_tax == 0:
                continue

            # Deduplicate same-named taxes (e.g. Medicare appears once)
            key = (bracket.tax_type, bracket.tax_name)
            if key in seen_types:
                continue
            seen_types.add(key)

            tax_lines.append(TaxLine(
                description=bracket.tax_name,
                tax_type=bracket.tax_type,
                employee_amount=period_employee_tax,
                employer_amount=period_employer_tax,
                rate=bracket.employee_rate,
            ))

        return tax_lines


# ── Main engine ───────────────────────────────────────────────

class PayrollEngine:

    def __init__(self, country_registry):
        self._registry = country_registry
        self._tax_calc = TaxCalculator()

    def calculate(self, inp: PayrollInput) -> PayrollResult:
        result = PayrollResult(
            employee_id=inp.employee_id,
            employee_name=f"{inp.first_name} {inp.last_name}",
            pay_period_start=inp.pay_period_start,
            pay_period_end=inp.pay_period_end,
            currency_code=inp.currency_code,
            country_code=inp.country_code,
            employee_type=inp.type_code,
            regular_hours=inp.regular_hours,
            overtime_hours=inp.overtime_hours,
            total_hours=inp.regular_hours + inp.overtime_hours,
        )

        country = self._registry.get(inp.country_code)

        # ── Step 1: Calculate gross earnings ─────────────────
        self._calculate_earnings(inp, result)

        # ── Step 2: Add bonuses ───────────────────────────────
        for bonus in inp.bonuses:
            result.earnings.append(EarningLine(
                description=bonus.get("description", "Bonus"),
                amount=round(float(bonus.get("amount", 0)), 2),
            ))
        result.gross_pay = round(sum(e.amount for e in result.earnings), 2)

        # ── Step 3: Pre-tax deductions ────────────────────────
        for ded in inp.deductions:
            if not ded.get("pre_tax"):
                continue
            amount = self._resolve_deduction(ded, result.gross_pay)
            if amount > 0:
                result.pre_tax_deductions.append(DeductionLine(
                    description=ded.get("description", ded.get("code", "Deduction")),
                    amount=amount,
                    is_pre_tax=True,
                ))
        result.total_pre_tax_deductions = round(
            sum(d.amount for d in result.pre_tax_deductions), 2
        )

        # ── Step 4: Taxable income ────────────────────────────
        result.taxable_income = round(
            result.gross_pay - result.total_pre_tax_deductions, 2
        )

        # ── Step 5: Calculate taxes ───────────────────────────
        tax_lines = self._tax_calc.calculate(
            taxable_income_period=result.taxable_income,
            pay_periods=inp.pay_periods_per_year,
            tax_brackets=country.tax_brackets,
            employee_type=inp.type_code,
        )
        result.taxes = tax_lines
        result.total_employee_tax = round(sum(t.employee_amount for t in tax_lines), 2)
        result.total_employer_tax = round(sum(t.employer_amount for t in tax_lines), 2)

        # ── Step 6: Post-tax deductions ───────────────────────
        for ded in inp.deductions:
            if ded.get("pre_tax"):
                continue
            amount = self._resolve_deduction(ded, result.gross_pay)
            if amount > 0:
                result.post_tax_deductions.append(DeductionLine(
                    description=ded.get("description", ded.get("code", "Deduction")),
                    amount=amount,
                    is_pre_tax=False,
                ))
        result.total_post_tax_deductions = round(
            sum(d.amount for d in result.post_tax_deductions), 2
        )

        # ── Step 7: Net pay ───────────────────────────────────
        result.net_pay = round(
            result.gross_pay
            - result.total_pre_tax_deductions
            - result.total_employee_tax
            - result.total_post_tax_deductions,
            2,
        )

        return result

    def _calculate_earnings(self, inp: PayrollInput, result: PayrollResult):
        """Calculate base earnings based on employee type."""

        if inp.type_code in ("FULLTIME",) and inp.base_salary:
            # Salaried: divide annual salary by pay periods
            period_salary = round(inp.base_salary / inp.pay_periods_per_year, 2)
            result.earnings.append(EarningLine("Base salary", period_salary))

        elif inp.type_code in ("HOURLY", "PARTTIME") and inp.hourly_rate:
            # Hourly: regular + overtime
            regular_pay  = round(inp.regular_hours * inp.hourly_rate, 2)
            overtime_pay = round(
                inp.overtime_hours * inp.hourly_rate * inp.overtime_multiplier, 2
            )
            result.earnings.append(EarningLine("Regular pay", regular_pay, inp.regular_hours))
            if overtime_pay > 0:
                result.earnings.append(EarningLine("Overtime pay", overtime_pay, inp.overtime_hours))

        elif inp.type_code == "CONTRACT":
            # Contractors: fixed period fee (stored as base_salary / periods)
            if inp.base_salary:
                period_fee = round(inp.base_salary / inp.pay_periods_per_year, 2)
                result.earnings.append(EarningLine("Contract fee", period_fee))
            elif inp.hourly_rate:
                fee = round((inp.regular_hours + inp.overtime_hours) * inp.hourly_rate, 2)
                result.earnings.append(EarningLine("Contract fee", fee,
                                                    inp.regular_hours + inp.overtime_hours))

        elif inp.type_code == "INTERN" and inp.hourly_rate:
            pay = round(inp.regular_hours * inp.hourly_rate, 2)
            result.earnings.append(EarningLine("Intern pay", pay, inp.regular_hours))

    def _resolve_deduction(self, ded: dict, gross: float) -> float:
        if ded.get("amount"):
            return round(float(ded["amount"]), 2)
        elif ded.get("percentage"):
            return round(gross * float(ded["percentage"]), 2)
        return 0.0

    def format_payslip(self, result: PayrollResult) -> str:
        """Return a formatted text payslip summary."""
        ccy = result.currency_code
        sep = "─" * 52
        lines = [
            f"\n{'PAYSLIP':^52}",
            f"{result.employee_name:^52}",
            f"{result.employee_type} — {result.country_code} — {ccy}",
            f"Period: {result.pay_period_start} to {result.pay_period_end}",
            sep,
            "EARNINGS",
        ]
        for e in result.earnings:
            hrs = f"  ({e.hours:.1f}h)" if e.hours else ""
            lines.append(f"  {e.description:<30} {ccy} {e.amount:>10,.2f}{hrs}")

        if result.bonuses if hasattr(result, 'bonuses') else False:
            pass

        lines += [
            f"  {'Gross pay':<30} {ccy} {result.gross_pay:>10,.2f}",
            sep,
        ]

        if result.pre_tax_deductions:
            lines.append("PRE-TAX DEDUCTIONS")
            for d in result.pre_tax_deductions:
                lines.append(f"  {d.description:<30} {ccy} {d.amount:>10,.2f}")
            lines.append(f"  {'Taxable income':<30} {ccy} {result.taxable_income:>10,.2f}")
            lines.append(sep)

        lines.append("TAXES")
        for t in result.taxes:
            lines.append(f"  {t.description:<30} {ccy} {t.employee_amount:>10,.2f}")
        lines += [
            f"  {'Total tax':<30} {ccy} {result.total_employee_tax:>10,.2f}",
            sep,
        ]

        if result.post_tax_deductions:
            lines.append("POST-TAX DEDUCTIONS")
            for d in result.post_tax_deductions:
                lines.append(f"  {d.description:<30} {ccy} {d.amount:>10,.2f}")
            lines.append(sep)

        lines += [
            f"  {'NET PAY':<30} {ccy} {result.net_pay:>10,.2f}",
            sep,
        ]

        if result.total_hours > 0:
            lines.append(f"  Regular hrs: {result.regular_hours:.1f}  |  OT hrs: {result.overtime_hours:.1f}  |  Total: {result.total_hours:.1f}")

        return "\n".join(lines)
