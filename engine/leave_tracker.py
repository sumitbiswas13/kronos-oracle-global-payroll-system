"""
Leave Tracker Engine
Manages leave balances, requests, approvals, and accruals.
Country-aware — different entitlements per country and employee type.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
from enum import Enum


class LeaveStatus(str, Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class LeaveCode(str, Enum):
    ANNUAL      = "ANNUAL"
    SICK        = "SICK"
    MATERNITY   = "MATERNITY"
    PATERNITY   = "PATERNITY"
    BEREAVEMENT = "BEREAVEMENT"
    UNPAID      = "UNPAID"
    PUBLIC      = "PUBLIC"


@dataclass
class LeaveEntitlement:
    leave_code: str
    leave_name: str
    days_per_year: float
    is_paid: bool
    carries_over: bool
    max_carryover: float = 5.0


@dataclass
class LeaveBalance:
    employee_id: int
    leave_code: str
    year: int
    entitled_days: float
    taken_days: float = 0.0
    pending_days: float = 0.0
    carried_over: float = 0.0

    @property
    def remaining_days(self) -> float:
        return round(self.entitled_days + self.carried_over - self.taken_days - self.pending_days, 1)


@dataclass
class LeaveRequest:
    request_id: int
    employee_id: int
    leave_code: str
    start_date: date
    end_date: date
    days_requested: float
    status: LeaveStatus = LeaveStatus.PENDING
    approved_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: date = field(default_factory=date.today)
    rejection_reason: Optional[str] = None


# ── Country leave entitlements ────────────────────────────────
COUNTRY_ENTITLEMENTS = {
    "US": [
        LeaveEntitlement("ANNUAL",      "PTO",              15.0, True,  True,  5.0),
        LeaveEntitlement("SICK",        "Sick leave",       10.0, True,  False, 0.0),
        LeaveEntitlement("BEREAVEMENT", "Bereavement",       5.0, True,  False, 0.0),
        LeaveEntitlement("MATERNITY",   "FMLA Maternity",   60.0, False, False, 0.0),
        LeaveEntitlement("PATERNITY",   "FMLA Paternity",   10.0, False, False, 0.0),
        LeaveEntitlement("UNPAID",      "Unpaid leave",      0.0, False, False, 0.0),
    ],
    "GB": [
        LeaveEntitlement("ANNUAL",      "Annual leave",     28.0, True,  True,  8.0),
        LeaveEntitlement("SICK",        "Sick leave (SSP)", 28.0, True,  False, 0.0),
        LeaveEntitlement("MATERNITY",   "Maternity leave",  52.0, True,  False, 0.0),
        LeaveEntitlement("PATERNITY",   "Paternity leave",   2.0, True,  False, 0.0),
        LeaveEntitlement("BEREAVEMENT", "Bereavement",       5.0, True,  False, 0.0),
        LeaveEntitlement("UNPAID",      "Unpaid leave",      0.0, False, False, 0.0),
    ],
    "IN": [
        LeaveEntitlement("ANNUAL",      "Earned leave",     21.0, True,  True,  30.0),
        LeaveEntitlement("SICK",        "Sick leave",       12.0, True,  False, 0.0),
        LeaveEntitlement("MATERNITY",   "Maternity leave",  84.0, True,  False, 0.0),
        LeaveEntitlement("PATERNITY",   "Paternity leave",  15.0, True,  False, 0.0),
        LeaveEntitlement("BEREAVEMENT", "Bereavement",       3.0, True,  False, 0.0),
        LeaveEntitlement("UNPAID",      "Leave without pay", 0.0, False, False, 0.0),
    ],
    "AU": [
        LeaveEntitlement("ANNUAL",      "Annual leave",     20.0, True,  True,  20.0),
        LeaveEntitlement("SICK",        "Personal/carer's", 10.0, True,  True,  10.0),
        LeaveEntitlement("MATERNITY",   "Parental leave",   52.0, True,  False, 0.0),
        LeaveEntitlement("PATERNITY",   "Paternity leave",  10.0, True,  False, 0.0),
        LeaveEntitlement("BEREAVEMENT", "Compassionate",     2.0, True,  False, 0.0),
        LeaveEntitlement("UNPAID",      "Unpaid leave",      0.0, False, False, 0.0),
    ],
}


class LeaveTracker:
    """
    Manages leave balances and requests.
    In production, all data is persisted in Oracle GPS_LEAVE_* tables.
    This engine handles all the business logic.
    """

    def __init__(self):
        self._balances: dict[tuple, LeaveBalance] = {}
        self._requests: list[LeaveRequest] = []
        self._next_id = 1

    def initialise_employee(
        self,
        employee_id: int,
        country_code: str,
        year: int,
        hire_date: Optional[date] = None,
    ) -> list[LeaveBalance]:
        """
        Set up leave balances for an employee for a given year.
        Prorates entitlements for new hires joining mid-year.
        """
        entitlements = COUNTRY_ENTITLEMENTS.get(country_code.upper(), [])
        balances = []

        for ent in entitlements:
            days = ent.days_per_year

            # Prorate for new hires
            if hire_date and hire_date.year == year:
                days_in_year  = 366 if year % 4 == 0 else 365
                days_remaining = (date(year, 12, 31) - hire_date).days + 1
                days = round(days * days_remaining / days_in_year, 1)

            bal = LeaveBalance(
                employee_id=employee_id,
                leave_code=ent.leave_code,
                year=year,
                entitled_days=days,
            )
            self._balances[(employee_id, ent.leave_code, year)] = bal
            balances.append(bal)

        return balances

    def get_balance(self, employee_id: int, leave_code: str, year: int) -> Optional[LeaveBalance]:
        return self._balances.get((employee_id, leave_code, year))

    def get_all_balances(self, employee_id: int, year: int) -> list[LeaveBalance]:
        return [b for (eid, _, yr), b in self._balances.items()
                if eid == employee_id and yr == year]

    def request_leave(
        self,
        employee_id: int,
        leave_code: str,
        start_date: date,
        end_date: date,
        notes: Optional[str] = None,
    ) -> LeaveRequest:
        """Submit a leave request with validation."""
        days = self._count_working_days(start_date, end_date)
        year = start_date.year

        # Validate balance
        bal = self.get_balance(employee_id, leave_code, year)
        if bal and bal.remaining_days < days:
            raise ValueError(
                f"Insufficient {leave_code} balance. "
                f"Requested: {days} days, Available: {bal.remaining_days} days"
            )

        req = LeaveRequest(
            request_id=self._next_id,
            employee_id=employee_id,
            leave_code=leave_code,
            start_date=start_date,
            end_date=end_date,
            days_requested=days,
            notes=notes,
        )
        self._next_id += 1
        self._requests.append(req)

        # Mark as pending in balance
        if bal:
            bal.pending_days += days

        return req

    def approve_request(self, request_id: int, approved_by: int) -> LeaveRequest:
        req = self._get_request(request_id)
        if req.status != LeaveStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        bal = self.get_balance(req.employee_id, req.leave_code, req.start_date.year)
        if bal:
            bal.pending_days -= req.days_requested
            bal.taken_days   += req.days_requested

        req.status      = LeaveStatus.APPROVED
        req.approved_by = approved_by
        return req

    def reject_request(self, request_id: int, approved_by: int, reason: str) -> LeaveRequest:
        req = self._get_request(request_id)
        if req.status != LeaveStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        bal = self.get_balance(req.employee_id, req.leave_code, req.start_date.year)
        if bal:
            bal.pending_days -= req.days_requested

        req.status           = LeaveStatus.REJECTED
        req.approved_by      = approved_by
        req.rejection_reason = reason
        return req

    def get_requests(
        self,
        employee_id: Optional[int] = None,
        status: Optional[LeaveStatus] = None,
        year: Optional[int] = None,
    ) -> list[LeaveRequest]:
        reqs = self._requests
        if employee_id:
            reqs = [r for r in reqs if r.employee_id == employee_id]
        if status:
            reqs = [r for r in reqs if r.status == status]
        if year:
            reqs = [r for r in reqs if r.start_date.year == year]
        return sorted(reqs, key=lambda r: r.created_at, reverse=True)

    def carry_over_balances(self, employee_id: int, from_year: int) -> list[LeaveBalance]:
        """Process year-end carryover into new year balances."""
        country_entitlements_flat = {
            e.leave_code: e
            for entitlements in COUNTRY_ENTITLEMENTS.values()
            for e in entitlements
        }
        carried = []
        for bal in self.get_all_balances(employee_id, from_year):
            ent = country_entitlements_flat.get(bal.leave_code)
            if not ent or not ent.carries_over:
                continue
            carryover = min(bal.remaining_days, ent.max_carryover)
            if carryover > 0:
                new_bal = self.get_balance(employee_id, bal.leave_code, from_year + 1)
                if new_bal:
                    new_bal.carried_over += carryover
                carried.append((bal.leave_code, carryover))
        return carried

    def _count_working_days(self, start: date, end: date) -> float:
        """Count working days between two dates (Mon–Fri)."""
        count = 0
        current = start
        while current <= end:
            if current.weekday() < 5:
                count += 1
            current += timedelta(days=1)
        return float(count)

    def _get_request(self, request_id: int) -> LeaveRequest:
        req = next((r for r in self._requests if r.request_id == request_id), None)
        if not req:
            raise ValueError(f"Request {request_id} not found")
        return req
