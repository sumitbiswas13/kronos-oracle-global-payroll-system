"""
Kronos Adapter
Simulates the UKG Workforce Central / UKG Pro REST API.
Swap MockKronosAdapter for RealKronosAdapter when live credentials are available.
Both implement the same KronosAdapterBase interface — no other code changes needed.
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


# ── Data models ───────────────────────────────────────────────

@dataclass
class KronosShift:
    employee_id: str            # Kronos employee ID
    shift_date: date
    scheduled_start: str        # HH:MM
    scheduled_end: str          # HH:MM
    actual_start: Optional[str]
    actual_end: Optional[str]
    hours_worked: float
    is_overtime: bool
    department: str
    location_code: str


@dataclass
class KronosTimecard:
    employee_id: str
    period_start: date
    period_end: date
    regular_hours: float
    overtime_hours: float
    double_time_hours: float
    pto_hours: float
    sick_hours: float
    total_hours: float
    shifts: list[KronosShift] = field(default_factory=list)
    approved: bool = False
    approved_by: Optional[str] = None


@dataclass
class KronosEmployee:
    kronos_id: str
    employee_number: str        # Maps to GPS_EMPLOYEES.EXTERNAL_ID
    first_name: str
    last_name: str
    email: str
    department: str
    location_code: str
    pay_rule: str               # HOURLY | SALARIED | PARTTIME
    hire_date: date
    active: bool = True


# ── Base interface ────────────────────────────────────────────

class KronosAdapterBase(ABC):

    @abstractmethod
    def get_employee(self, kronos_id: str) -> Optional[KronosEmployee]:
        pass

    @abstractmethod
    def get_all_employees(self, location_code: Optional[str] = None) -> list[KronosEmployee]:
        pass

    @abstractmethod
    def get_timecard(
        self,
        kronos_id: str,
        period_start: date,
        period_end: date,
    ) -> Optional[KronosTimecard]:
        pass

    @abstractmethod
    def get_timecards_for_period(
        self,
        period_start: date,
        period_end: date,
        location_code: Optional[str] = None,
    ) -> list[KronosTimecard]:
        pass


# ── Mock adapter ──────────────────────────────────────────────

class MockKronosAdapter(KronosAdapterBase):
    """
    Realistic mock of the Kronos UKG API.
    Generates deterministic data based on employee IDs so results
    are consistent across multiple calls in the same demo run.
    Replace with RealKronosAdapter when live API credentials are available.
    """

    MOCK_EMPLOYEES = [
        KronosEmployee("KRN001", "EMP001", "James",    "Carter",   "jcarter@acme.com",    "Engineering",  "US-NYC", "SALARIED",  date(2019, 3, 15)),
        KronosEmployee("KRN002", "EMP002", "Priya",    "Sharma",   "psharma@acme.com",    "Engineering",  "IN-BLR", "SALARIED",  date(2020, 7, 1)),
        KronosEmployee("KRN003", "EMP003", "Oliver",   "Bennett",  "obennett@acme.com",   "Finance",      "GB-LON", "SALARIED",  date(2018, 11, 20)),
        KronosEmployee("KRN004", "EMP004", "Chloe",    "Thompson", "cthompson@acme.com",  "Operations",   "AU-SYD", "SALARIED",  date(2021, 2, 8)),
        KronosEmployee("KRN005", "EMP005", "Marcus",   "Williams", "mwilliams@acme.com",  "Warehouse",    "US-NYC", "HOURLY",    date(2022, 5, 14)),
        KronosEmployee("KRN006", "EMP006", "Aisha",    "Patel",    "apatel@acme.com",     "Support",      "IN-MUM", "HOURLY",    date(2023, 1, 9)),
        KronosEmployee("KRN007", "EMP007", "Emma",     "Wilson",   "ewilson@acme.com",    "Marketing",    "GB-LON", "PARTTIME",  date(2022, 9, 5)),
        KronosEmployee("KRN008", "EMP008", "Liam",     "Johnson",  "ljohnson@acme.com",   "IT",           "AU-MEL", "HOURLY",    date(2021, 6, 30)),
        KronosEmployee("KRN009", "EMP009", "Sofia",    "Martinez", "smartinez@acme.com",  "Sales",        "US-LAX", "SALARIED",  date(2017, 4, 22)),
        KronosEmployee("KRN010", "EMP010", "Raj",      "Kumar",    "rkumar@acme.com",     "Engineering",  "IN-DEL", "CONTRACT",  date(2023, 8, 1)),
    ]

    def _make_shifts(
        self,
        kronos_id: str,
        period_start: date,
        period_end: date,
        pay_rule: str,
    ) -> list[KronosShift]:
        """Generate realistic shifts for the pay period."""
        shifts = []
        rng = random.Random(kronos_id + str(period_start))
        current = period_start

        hours_per_day = 8.0 if pay_rule != "PARTTIME" else 4.0

        while current <= period_end:
            if current.weekday() < 5:  # Mon–Fri
                # Occasionally miss a day (sick/leave)
                if rng.random() > 0.05:
                    actual_hours = hours_per_day + rng.uniform(-0.25, 0.5)
                    actual_hours = round(actual_hours, 2)
                    overtime = max(0.0, round(actual_hours - 8.0, 2)) if pay_rule == "HOURLY" else 0.0
                    shifts.append(KronosShift(
                        employee_id=kronos_id,
                        shift_date=current,
                        scheduled_start="09:00",
                        scheduled_end="17:00" if pay_rule != "PARTTIME" else "13:00",
                        actual_start="09:00",
                        actual_end="17:00",
                        hours_worked=actual_hours,
                        is_overtime=overtime > 0,
                        department=next(e.department for e in self.MOCK_EMPLOYEES if e.kronos_id == kronos_id),
                        location_code=next(e.location_code for e in self.MOCK_EMPLOYEES if e.kronos_id == kronos_id),
                    ))
            current += timedelta(days=1)
        return shifts

    def get_employee(self, kronos_id: str) -> Optional[KronosEmployee]:
        return next((e for e in self.MOCK_EMPLOYEES if e.kronos_id == kronos_id), None)

    def get_all_employees(self, location_code: Optional[str] = None) -> list[KronosEmployee]:
        employees = [e for e in self.MOCK_EMPLOYEES if e.active]
        if location_code:
            employees = [e for e in employees if e.location_code == location_code]
        return employees

    def get_timecard(
        self,
        kronos_id: str,
        period_start: date,
        period_end: date,
    ) -> Optional[KronosTimecard]:
        emp = self.get_employee(kronos_id)
        if not emp:
            return None

        shifts = self._make_shifts(kronos_id, period_start, period_end, emp.pay_rule)
        regular   = sum(min(s.hours_worked, 8.0) for s in shifts if not s.is_overtime)
        overtime  = sum(s.hours_worked - 8.0 for s in shifts if s.is_overtime)
        overtime  = max(0.0, round(overtime, 2))

        rng = random.Random(kronos_id + "pto" + str(period_start))
        pto_hours  = round(rng.choice([0, 0, 0, 8.0]), 1)
        sick_hours = round(rng.choice([0, 0, 8.0]), 1)

        return KronosTimecard(
            employee_id=kronos_id,
            period_start=period_start,
            period_end=period_end,
            regular_hours=round(regular, 2),
            overtime_hours=overtime,
            double_time_hours=0.0,
            pto_hours=pto_hours,
            sick_hours=sick_hours,
            total_hours=round(regular + overtime + pto_hours + sick_hours, 2),
            shifts=shifts,
            approved=True,
            approved_by="SYSTEM",
        )

    def get_timecards_for_period(
        self,
        period_start: date,
        period_end: date,
        location_code: Optional[str] = None,
    ) -> list[KronosTimecard]:
        employees = self.get_all_employees(location_code=location_code)
        return [
            tc for e in employees
            if (tc := self.get_timecard(e.kronos_id, period_start, period_end)) is not None
        ]


# ── Real adapter stub (swap in when live) ────────────────────

class RealKronosAdapter(KronosAdapterBase):
    """
    Production adapter for UKG Pro / Workforce Central REST API.
    Swap MockKronosAdapter → RealKronosAdapter in your DI config.
    No other code changes required.
    """

    def __init__(self, base_url: str, client_id: str, client_secret: str, tenant_id: str):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self._token: Optional[str] = None

    def _get_token(self) -> str:
        """Authenticate with UKG and return a bearer token."""
        import httpx
        resp = httpx.post(
            f"{self.base_url}/authentication/access_token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "tenant_id": self.tenant_id,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _headers(self) -> dict:
        if not self._token:
            self._token = self._get_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def get_employee(self, kronos_id: str) -> Optional[KronosEmployee]:
        raise NotImplementedError("Wire up UKG /v1/commons/persons endpoint")

    def get_all_employees(self, location_code=None) -> list[KronosEmployee]:
        raise NotImplementedError("Wire up UKG /v1/commons/persons endpoint")

    def get_timecard(self, kronos_id, period_start, period_end) -> Optional[KronosTimecard]:
        raise NotImplementedError("Wire up UKG /v1/timekeeping/timecard_approvals endpoint")

    def get_timecards_for_period(self, period_start, period_end, location_code=None) -> list[KronosTimecard]:
        raise NotImplementedError("Wire up UKG /v1/timekeeping/timecard_approvals endpoint")
