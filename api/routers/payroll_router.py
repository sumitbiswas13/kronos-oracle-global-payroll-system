"""
Payroll Router — /payroll endpoints
"""

import os
from datetime import date
from dataclasses import dataclass, field
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.auth import get_current_user, require_admin, require_manager_or_admin, CurrentUser
from adapters.kronos_adapter import MockKronosAdapter
from engine.payroll_engine import PayrollEngine, PayrollInput
from engine.pdf_generator import PayslipPDFGenerator

router = APIRouter(prefix="/payroll", tags=["Payroll"])


# ── Inline mock registry ──────────────────────────────────────
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
                TaxBracket("INCOME","Federal 22%",0.22,0,47151,100525,"ALL"),
                TaxBracket("SOCIAL_SECURITY","FICA",0.062,0.062,0,168600,"ALL"),
                TaxBracket("MEDICARE","Medicare",0.0145,0.0145,0,None,"ALL"),
            ]),
            "GB": CountryConfig("GB","United Kingdom","GBP","04-06","MONTHLY",[
                TaxBracket("INCOME","Basic Rate 20%",0.20,0,12571,50270,"ALL"),
                TaxBracket("INCOME","Higher Rate 40%",0.40,0,50271,125140,"ALL"),
                TaxBracket("NI","National Insurance",0.08,0.138,12570,50270,"ALL"),
            ]),
            "IN": CountryConfig("IN","India","INR","04-01","MONTHLY",[
                TaxBracket("INCOME","30% Band",0.30,0,1500001,None,"ALL"),
                TaxBracket("PF","Provident Fund",0.12,0.12,0,None,"FULLTIME"),
            ]),
            "AU": CountryConfig("AU","Australia","AUD","07-01","MONTHLY",[
                TaxBracket("INCOME","32.5% Band",0.325,0,45001,120000,"ALL"),
                TaxBracket("MEDICARE","Medicare",0.02,0,0,None,"ALL"),
            ]),
        }
    def get(self, code): return self._c[code.upper()]

EMPLOYEE_CONFIG = {
    "KRN001":{"country":"US","currency":"USD","type":"FULLTIME","salary":95000, "rate":None,
              "deductions":[{"description":"401(k) 6%","percentage":0.06,"pre_tax":True},
                            {"description":"Health Insurance","amount":250,"pre_tax":True}]},
    "KRN002":{"country":"IN","currency":"INR","type":"FULLTIME","salary":1800000,"rate":None,
              "deductions":[{"description":"Provident Fund 12%","percentage":0.12,"pre_tax":True}]},
    "KRN003":{"country":"GB","currency":"GBP","type":"FULLTIME","salary":65000, "rate":None,
              "deductions":[{"description":"Workplace Pension 5%","percentage":0.05,"pre_tax":True}]},
    "KRN004":{"country":"AU","currency":"AUD","type":"FULLTIME","salary":95000, "rate":None,
              "deductions":[{"description":"Superannuation 11.5%","percentage":0.115,"pre_tax":False}]},
    "KRN005":{"country":"US","currency":"USD","type":"HOURLY","salary":None,"rate":28.0,"deductions":[]},
    "KRN006":{"country":"IN","currency":"INR","type":"HOURLY","salary":None,"rate":450.0,"deductions":[]},
    "KRN007":{"country":"GB","currency":"GBP","type":"PARTTIME","salary":None,"rate":18.0,"deductions":[]},
    "KRN008":{"country":"AU","currency":"AUD","type":"HOURLY","salary":None,"rate":35.0,"deductions":[]},
    "KRN009":{"country":"US","currency":"USD","type":"FULLTIME","salary":110000,"rate":None,
              "deductions":[{"description":"401(k) 8%","percentage":0.08,"pre_tax":True}]},
    "KRN010":{"country":"IN","currency":"INR","type":"CONTRACT","salary":2400000,"rate":None,"deductions":[]},
}
PAY_PERIODS  = {"BIWEEKLY":26,"MONTHLY":12}
COUNTRY_FREQ = {"US":"BIWEEKLY","GB":"MONTHLY","IN":"MONTHLY","AU":"MONTHLY"}
EMP_KRONOS   = {1:"KRN001",2:"KRN002",3:"KRN003",4:"KRN004",5:"KRN005",
                6:"KRN006",7:"KRN007",8:"KRN008",9:"KRN009",10:"KRN010"}

kronos   = MockKronosAdapter()
registry = MockRegistry()
engine   = PayrollEngine(registry)
pdf_gen  = PayslipPDFGenerator(output_dir="output/payslips")


# ── Request models ────────────────────────────────────────────
class RunPayrollRequest(BaseModel):
    period_start: date
    period_end: date
    country_code: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/run", summary="Trigger a payroll run")
def run_payroll(
    req: RunPayrollRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    """Trigger payroll calculation for a pay period. Admin only."""
    results = []
    for emp in kronos.get_all_employees():
        cfg = EMPLOYEE_CONFIG[emp.kronos_id]
        if req.country_code and cfg["country"] != req.country_code.upper():
            continue
        tc      = kronos.get_timecard(emp.kronos_id, req.period_start, req.period_end)
        freq    = COUNTRY_FREQ[cfg["country"]]
        periods = PAY_PERIODS[freq]
        inp = PayrollInput(
            employee_id=int(emp.kronos_id.replace("KRN","")),
            first_name=emp.first_name, last_name=emp.last_name,
            type_code=cfg["type"], country_code=cfg["country"],
            currency_code=cfg["currency"], base_salary=cfg["salary"],
            hourly_rate=cfg["rate"], regular_hours=tc.regular_hours,
            overtime_hours=tc.overtime_hours, pto_hours=tc.pto_hours,
            sick_hours=tc.sick_hours, pay_period_start=req.period_start,
            pay_period_end=req.period_end, pay_periods_per_year=periods,
            deductions=cfg["deductions"],
        )
        r = engine.calculate(inp)
        pdf_gen.generate(r, company_name="Acme Global Corp")
        results.append({
            "employee_id":  r.employee_id,
            "name":         r.employee_name,
            "country":      r.country_code,
            "currency":     r.currency_code,
            "gross_pay":    r.gross_pay,
            "total_tax":    r.total_employee_tax,
            "net_pay":      r.net_pay,
        })

    total_net = sum(r["net_pay"] for r in results)
    return {
        "status":       "complete",
        "period_start": req.period_start,
        "period_end":   req.period_end,
        "employees":    len(results),
        "total_net":    total_net,
        "payslips":     results,
    }


@router.get("/payslips/{employee_id}", summary="Get payslip summary for an employee")
def get_payslips(
    employee_id: int,
    period_start: date,
    period_end: date,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get payslip data. Employees can only view their own."""
    if current_user.role == "EMPLOYEE" and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own payslips")

    kronos_id = EMP_KRONOS.get(employee_id)
    if not kronos_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    cfg     = EMPLOYEE_CONFIG[kronos_id]
    emp     = kronos.get_employee(kronos_id)
    tc      = kronos.get_timecard(kronos_id, period_start, period_end)
    freq    = COUNTRY_FREQ[cfg["country"]]
    periods = PAY_PERIODS[freq]

    inp = PayrollInput(
        employee_id=employee_id,
        first_name=emp.first_name, last_name=emp.last_name,
        type_code=cfg["type"], country_code=cfg["country"],
        currency_code=cfg["currency"], base_salary=cfg["salary"],
        hourly_rate=cfg["rate"], regular_hours=tc.regular_hours,
        overtime_hours=tc.overtime_hours, pto_hours=tc.pto_hours,
        sick_hours=tc.sick_hours, pay_period_start=period_start,
        pay_period_end=period_end, pay_periods_per_year=periods,
        deductions=cfg["deductions"],
    )
    r = engine.calculate(inp)

    return {
        "employee_id":          r.employee_id,
        "employee_name":        r.employee_name,
        "employee_type":        r.employee_type,
        "country":              r.country_code,
        "currency":             r.currency_code,
        "period_start":         r.pay_period_start,
        "period_end":           r.pay_period_end,
        "gross_pay":            r.gross_pay,
        "total_pre_tax_ded":    r.total_pre_tax_deductions,
        "taxable_income":       r.taxable_income,
        "total_tax":            r.total_employee_tax,
        "total_post_tax_ded":   r.total_post_tax_deductions,
        "net_pay":              r.net_pay,
        "regular_hours":        r.regular_hours,
        "overtime_hours":       r.overtime_hours,
        "earnings":   [{"description": e.description, "amount": e.amount} for e in r.earnings],
        "taxes":      [{"description": t.description, "amount": t.employee_amount} for t in r.taxes],
        "deductions": [{"description": d.description, "amount": d.amount} for d in r.pre_tax_deductions + r.post_tax_deductions],
    }


@router.get("/payslips/{employee_id}/pdf", summary="Download payslip as PDF")
def download_payslip_pdf(
    employee_id: int,
    period_start: date,
    period_end: date,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Download payslip PDF. Employees can only download their own."""
    if current_user.role == "EMPLOYEE" and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="You can only download your own payslip")

    kronos_id = EMP_KRONOS.get(employee_id)
    if not kronos_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    cfg     = EMPLOYEE_CONFIG[kronos_id]
    emp     = kronos.get_employee(kronos_id)
    tc      = kronos.get_timecard(kronos_id, period_start, period_end)
    freq    = COUNTRY_FREQ[cfg["country"]]
    periods = PAY_PERIODS[freq]

    inp = PayrollInput(
        employee_id=employee_id,
        first_name=emp.first_name, last_name=emp.last_name,
        type_code=cfg["type"], country_code=cfg["country"],
        currency_code=cfg["currency"], base_salary=cfg["salary"],
        hourly_rate=cfg["rate"], regular_hours=tc.regular_hours,
        overtime_hours=tc.overtime_hours, pto_hours=tc.pto_hours,
        sick_hours=tc.sick_hours, pay_period_start=period_start,
        pay_period_end=period_end, pay_periods_per_year=periods,
        deductions=cfg["deductions"],
    )
    r    = engine.calculate(inp)
    path = pdf_gen.generate(r, company_name="Acme Global Corp")

    return FileResponse(
        path=path,
        media_type="application/pdf",
        filename=os.path.basename(path),
    )
