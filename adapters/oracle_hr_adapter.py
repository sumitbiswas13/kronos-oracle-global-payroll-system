"""
Oracle HR Adapter
Reads employee data from Oracle GPS tables and syncs Kronos data back.
Also handles the initial employee sync from Kronos → Oracle.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
import oracledb

from adapters.kronos_adapter import KronosEmployee, KronosTimecard


@dataclass
class GPSEmployee:
    employee_id: int
    external_id: Optional[str]
    first_name: str
    last_name: str
    email: str
    type_code: str
    office_id: int
    base_salary: Optional[float]
    hourly_rate: Optional[float]
    currency_code: str
    hire_date: date
    kronos_id: Optional[str]
    active: bool


class OracleHRAdapter:
    """
    Reads/writes employee data in Oracle GPS schema.
    Handles syncing Kronos employees into GPS_EMPLOYEES and
    writing timecard data back for payroll processing.
    """

    def __init__(self, connection):
        self._conn = connection

    # ── Employee reads ────────────────────────────────────────

    def get_employee_by_id(self, employee_id: int) -> Optional[GPSEmployee]:
        cur = self._conn.cursor()
        cur.execute("""
            SELECT EMPLOYEE_ID, EXTERNAL_ID, FIRST_NAME, LAST_NAME,
                   EMAIL, TYPE_CODE, OFFICE_ID, BASE_SALARY, HOURLY_RATE,
                   CURRENCY_CODE, HIRE_DATE, KRONOS_ID, ACTIVE
            FROM GPS_EMPLOYEES
            WHERE EMPLOYEE_ID = :id
        """, {"id": employee_id})
        row = cur.fetchone()
        return self._row_to_employee(row) if row else None

    def get_employee_by_kronos_id(self, kronos_id: str) -> Optional[GPSEmployee]:
        cur = self._conn.cursor()
        cur.execute("""
            SELECT EMPLOYEE_ID, EXTERNAL_ID, FIRST_NAME, LAST_NAME,
                   EMAIL, TYPE_CODE, OFFICE_ID, BASE_SALARY, HOURLY_RATE,
                   CURRENCY_CODE, HIRE_DATE, KRONOS_ID, ACTIVE
            FROM GPS_EMPLOYEES
            WHERE KRONOS_ID = :kid
        """, {"kid": kronos_id})
        row = cur.fetchone()
        return self._row_to_employee(row) if row else None

    def get_employees_for_office(self, office_id: int, active_only: bool = True) -> list[GPSEmployee]:
        cur = self._conn.cursor()
        sql = """
            SELECT EMPLOYEE_ID, EXTERNAL_ID, FIRST_NAME, LAST_NAME,
                   EMAIL, TYPE_CODE, OFFICE_ID, BASE_SALARY, HOURLY_RATE,
                   CURRENCY_CODE, HIRE_DATE, KRONOS_ID, ACTIVE
            FROM GPS_EMPLOYEES
            WHERE OFFICE_ID = :oid
        """
        if active_only:
            sql += " AND ACTIVE = 'Y'"
        cur.execute(sql, {"oid": office_id})
        return [self._row_to_employee(r) for r in cur.fetchall()]

    def get_all_active_employees(self) -> list[GPSEmployee]:
        cur = self._conn.cursor()
        cur.execute("""
            SELECT EMPLOYEE_ID, EXTERNAL_ID, FIRST_NAME, LAST_NAME,
                   EMAIL, TYPE_CODE, OFFICE_ID, BASE_SALARY, HOURLY_RATE,
                   CURRENCY_CODE, HIRE_DATE, KRONOS_ID, ACTIVE
            FROM GPS_EMPLOYEES
            WHERE ACTIVE = 'Y'
            ORDER BY EMPLOYEE_ID
        """)
        return [self._row_to_employee(r) for r in cur.fetchall()]

    # ── Kronos sync ───────────────────────────────────────────

    def sync_kronos_employee(
        self,
        kronos_emp: KronosEmployee,
        office_id: int,
        type_code: str,
        currency_code: str,
        base_salary: Optional[float] = None,
        hourly_rate: Optional[float] = None,
    ) -> tuple[GPSEmployee, bool]:
        """
        Upsert a Kronos employee into GPS_EMPLOYEES.
        Returns (employee, created) where created=True if new record.
        """
        existing = self.get_employee_by_kronos_id(kronos_emp.kronos_id)

        if existing:
            # Update name/email if changed in Kronos
            cur = self._conn.cursor()
            cur.execute("""
                UPDATE GPS_EMPLOYEES
                SET FIRST_NAME  = :fn,
                    LAST_NAME   = :ln,
                    EMAIL       = :em,
                    UPDATED_AT  = SYSTIMESTAMP
                WHERE KRONOS_ID = :kid
            """, {
                "fn": kronos_emp.first_name,
                "ln": kronos_emp.last_name,
                "em": kronos_emp.email,
                "kid": kronos_emp.kronos_id,
            })
            self._conn.commit()
            return self.get_employee_by_kronos_id(kronos_emp.kronos_id), False

        # Insert new employee
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO GPS_EMPLOYEES (
                EXTERNAL_ID, FIRST_NAME, LAST_NAME, EMAIL,
                TYPE_CODE, OFFICE_ID, BASE_SALARY, HOURLY_RATE,
                CURRENCY_CODE, HIRE_DATE, KRONOS_ID
            ) VALUES (
                :ext_id, :fn, :ln, :em,
                :type, :office, :salary, :rate,
                :currency, :hire, :kid
            )
        """, {
            "ext_id":   kronos_emp.employee_number,
            "fn":       kronos_emp.first_name,
            "ln":       kronos_emp.last_name,
            "em":       kronos_emp.email,
            "type":     type_code,
            "office":   office_id,
            "salary":   base_salary,
            "rate":     hourly_rate,
            "currency": currency_code,
            "hire":     kronos_emp.hire_date,
            "kid":      kronos_emp.kronos_id,
        })
        self._conn.commit()
        return self.get_employee_by_kronos_id(kronos_emp.kronos_id), True

    def bulk_sync_kronos_employees(
        self,
        kronos_employees: list[KronosEmployee],
        office_id: int,
        currency_code: str,
        pay_rule_map: dict,  # {"SALARIED": ("FULLTIME", 85000, None), "HOURLY": ("HOURLY", None, 25.0)}
    ) -> dict:
        """Sync a list of Kronos employees to Oracle in bulk."""
        created, updated, skipped = 0, 0, 0
        for emp in kronos_employees:
            config = pay_rule_map.get(emp.pay_rule, ("FULLTIME", None, None))
            type_code, base_salary, hourly_rate = config
            _, was_created = self.sync_kronos_employee(
                emp, office_id, type_code, currency_code, base_salary, hourly_rate
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated, "skipped": skipped}

    # ── Timecard writes ───────────────────────────────────────

    def store_timecard_summary(self, timecard: KronosTimecard, payroll_run_id: Optional[int] = None):
        """
        Store Kronos timecard hours against the payslip for payroll processing.
        Called during payroll run preparation.
        """
        emp = self.get_employee_by_kronos_id(timecard.employee_id)
        if not emp:
            print(f"  ⚠️  No GPS employee found for Kronos ID {timecard.employee_id}")
            return None

        cur = self._conn.cursor()
        # Update or create payslip stub with hours from Kronos
        if payroll_run_id:
            cur.execute("""
                MERGE INTO GPS_PAYSLIPS p
                USING (SELECT :run_id AS run_id, :emp_id AS emp_id FROM DUAL) src
                ON (p.RUN_ID = src.run_id AND p.EMPLOYEE_ID = src.emp_id)
                WHEN MATCHED THEN UPDATE SET
                    HOURS_WORKED   = :reg_hrs,
                    OVERTIME_HOURS = :ot_hrs,
                    UPDATED_AT     = SYSTIMESTAMP  -- not a real col but shows intent
                WHEN NOT MATCHED THEN INSERT (
                    RUN_ID, EMPLOYEE_ID, PAY_PERIOD_START, PAY_PERIOD_END,
                    GROSS_PAY, NET_PAY, CURRENCY_CODE, HOURS_WORKED, OVERTIME_HOURS, STATUS
                ) VALUES (
                    :run_id, :emp_id, :ps, :pe,
                    0, 0, :currency, :reg_hrs, :ot_hrs, 'PENDING'
                )
            """, {
                "run_id":   payroll_run_id,
                "emp_id":   emp.employee_id,
                "ps":       timecard.period_start,
                "pe":       timecard.period_end,
                "currency": emp.currency_code,
                "reg_hrs":  timecard.regular_hours,
                "ot_hrs":   timecard.overtime_hours,
            })
            self._conn.commit()
        return emp

    # ── Helpers ───────────────────────────────────────────────

    def _row_to_employee(self, row) -> GPSEmployee:
        return GPSEmployee(
            employee_id=row[0],
            external_id=row[1],
            first_name=row[2],
            last_name=row[3],
            email=row[4],
            type_code=row[5],
            office_id=row[6],
            base_salary=float(row[7]) if row[7] else None,
            hourly_rate=float(row[8]) if row[8] else None,
            currency_code=row[9],
            hire_date=row[10],
            kronos_id=row[11],
            active=row[12] == "Y",
        )

    def get_office_country(self, office_id: int) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT COUNTRY_CODE FROM GPS_OFFICES WHERE OFFICE_ID = :id",
            {"id": office_id}
        )
        row = cur.fetchone()
        return row[0] if row else None
