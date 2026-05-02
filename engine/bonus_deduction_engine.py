"""
Bonus & Deductions Engine
Handles performance bonuses, signing bonuses, referral bonuses,
and flexible deduction rules per employee, country, and type.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from enum import Enum


class BonusType(str, Enum):
    PERFORMANCE  = "PERFORMANCE"    # Annual/quarterly performance bonus
    SIGNING      = "SIGNING"        # One-time signing bonus
    REFERRAL     = "REFERRAL"       # Employee referral bonus
    RETENTION    = "RETENTION"      # Retention/stay bonus
    SPOT         = "SPOT"           # Spot/recognition bonus
    HOLIDAY      = "HOLIDAY"        # Holiday/13th month bonus
    COMMISSION   = "COMMISSION"     # Sales commission


class DeductionMethod(str, Enum):
    FIXED        = "FIXED"          # Fixed amount per period
    PERCENT      = "PERCENT"        # % of gross pay
    TIERED       = "TIERED"         # Different rates at different income levels


@dataclass
class BonusRule:
    bonus_type: BonusType
    description: str
    calculation_method: str         # FIXED | PERCENT_OF_SALARY | PERCENT_OF_GROSS
    value: float                    # Amount or percentage
    pay_in_period: bool = True      # Pay in current period or defer
    is_taxable: bool = True
    applies_to: str = "ALL"        # ALL | FULLTIME | HOURLY etc.
    country_code: Optional[str] = None  # None = global


@dataclass
class BonusResult:
    bonus_type: BonusType
    description: str
    gross_amount: float
    tax_amount: float
    net_amount: float
    currency: str
    is_taxable: bool


@dataclass
class DeductionRule:
    deduction_code: str
    description: str
    method: DeductionMethod
    value: float                    # Amount or percentage
    is_pre_tax: bool = False
    country_code: Optional[str] = None
    applies_to: str = "ALL"
    max_amount: Optional[float] = None
    min_amount: Optional[float] = None


@dataclass
class DeductionResult:
    deduction_code: str
    description: str
    amount: float
    is_pre_tax: bool
    method: DeductionMethod


# ── Standard bonus rules by country ──────────────────────────
STANDARD_BONUS_RULES = {
    "IN": [
        BonusRule(BonusType.HOLIDAY, "Annual bonus (India statutory)",
                  "PERCENT_OF_SALARY", 8.33, True, True, "FULLTIME", "IN"),
    ],
    "AU": [
        BonusRule(BonusType.HOLIDAY, "Christmas bonus",
                  "FIXED", 500, True, True, "ALL", "AU"),
    ],
}

# ── Standard deduction rules by country ───────────────────────
STANDARD_DEDUCTION_RULES = {
    "US": [
        DeductionRule("HEALTH_INS",  "Health insurance",      DeductionMethod.FIXED,   250.0,  True,  "US"),
        DeductionRule("DENTAL_INS",  "Dental insurance",      DeductionMethod.FIXED,   30.0,   True,  "US"),
        DeductionRule("401K_DEFAULT","401(k) default 3%",     DeductionMethod.PERCENT, 0.03,   True,  "US", "FULLTIME"),
    ],
    "GB": [
        DeductionRule("PENSION_UK",  "Workplace pension 5%",  DeductionMethod.PERCENT, 0.05,   True,  "GB", "FULLTIME"),
        DeductionRule("STUDENT_LOAN","Student loan Plan 1",   DeductionMethod.PERCENT, 0.09,   False, "GB"),
    ],
    "IN": [
        DeductionRule("PF_INDIA",    "Provident fund 12%",    DeductionMethod.PERCENT, 0.12,   True,  "IN", "FULLTIME"),
        DeductionRule("ESI_INDIA",   "ESI contribution",      DeductionMethod.PERCENT, 0.0075, False, "IN"),
    ],
    "AU": [
        DeductionRule("SUPER_AU",    "Superannuation 11.5%",  DeductionMethod.PERCENT, 0.115,  False, "AU", "FULLTIME"),
    ],
}


class BonusDeductionEngine:
    """
    Calculates bonuses and deductions for a payroll period.
    Works alongside the PayrollEngine — outputs are fed into PayrollInput.
    """

    def calculate_bonus(
        self,
        bonus_rule: BonusRule,
        annual_salary: float,
        gross_period_pay: float,
        tax_rate: float,
        currency: str,
    ) -> BonusResult:
        """Calculate a bonus amount and its tax impact."""
        if bonus_rule.calculation_method == "FIXED":
            gross = bonus_rule.value
        elif bonus_rule.calculation_method == "PERCENT_OF_SALARY":
            gross = annual_salary * bonus_rule.value
        elif bonus_rule.calculation_method == "PERCENT_OF_GROSS":
            gross = gross_period_pay * bonus_rule.value
        else:
            gross = 0.0

        gross = round(gross, 2)
        tax   = round(gross * tax_rate, 2) if bonus_rule.is_taxable else 0.0
        net   = round(gross - tax, 2)

        return BonusResult(
            bonus_type=bonus_rule.bonus_type,
            description=bonus_rule.description,
            gross_amount=gross,
            tax_amount=tax,
            net_amount=net,
            currency=currency,
            is_taxable=bonus_rule.is_taxable,
        )

    def calculate_deduction(
        self,
        rule: DeductionRule,
        gross_pay: float,
    ) -> DeductionResult:
        """Calculate a deduction amount."""
        if rule.method == DeductionMethod.FIXED:
            amount = rule.value
        elif rule.method == DeductionMethod.PERCENT:
            amount = gross_pay * rule.value
        else:
            amount = 0.0

        if rule.max_amount:
            amount = min(amount, rule.max_amount)
        if rule.min_amount:
            amount = max(amount, rule.min_amount)

        return DeductionResult(
            deduction_code=rule.deduction_code,
            description=rule.description,
            amount=round(amount, 2),
            is_pre_tax=rule.is_pre_tax,
            method=rule.method,
        )

    def get_standard_deductions(
        self,
        country_code: str,
        employee_type: str,
        gross_pay: float,
    ) -> list[DeductionResult]:
        """Get all standard deductions for a country and employee type."""
        rules = STANDARD_DEDUCTION_RULES.get(country_code.upper(), [])
        results = []
        for rule in rules:
            if rule.applies_to not in ("ALL", employee_type):
                continue
            results.append(self.calculate_deduction(rule, gross_pay))
        return results

    def get_country_bonuses(
        self,
        country_code: str,
        employee_type: str,
        annual_salary: float,
        gross_period_pay: float,
        tax_rate: float,
        currency: str,
    ) -> list[BonusResult]:
        """Get all standard country-level bonuses."""
        rules = STANDARD_BONUS_RULES.get(country_code.upper(), [])
        results = []
        for rule in rules:
            if rule.applies_to not in ("ALL", employee_type):
                continue
            results.append(self.calculate_bonus(rule, annual_salary, gross_period_pay, tax_rate, currency))
        return results

    def calculate_performance_bonus(
        self,
        annual_salary: float,
        performance_rating: float,   # 1.0–5.0
        target_bonus_pct: float,     # e.g. 0.10 = 10% of salary
        tax_rate: float,
        currency: str,
    ) -> BonusResult:
        """
        Calculate a performance bonus.
        Rating 1.0 = 0% of target, 3.0 = 100%, 5.0 = 150%
        """
        multiplier = max(0.0, (performance_rating - 1.0) / 2.0 * 1.5)
        gross = round(annual_salary * target_bonus_pct * multiplier, 2)
        tax   = round(gross * tax_rate, 2)
        net   = round(gross - tax, 2)
        return BonusResult(
            bonus_type=BonusType.PERFORMANCE,
            description=f"Performance bonus (rating {performance_rating:.1f}/5.0)",
            gross_amount=gross,
            tax_amount=tax,
            net_amount=net,
            currency=currency,
            is_taxable=True,
        )
