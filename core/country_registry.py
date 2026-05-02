"""
Country Config Registry
Loads country-level payroll configuration from Oracle DB.
This is the core of the scalability design — adding a new country
means adding rows to the DB, not changing code.
"""

from dataclasses import dataclass, field
from typing import Optional
import oracledb


@dataclass
class TaxBracket:
    tax_type: str
    tax_name: str
    employee_rate: float
    employer_rate: float
    income_from: float
    income_to: Optional[float]    # None = no upper limit
    applies_to: str               # ALL | FULLTIME | HOURLY etc.


@dataclass
class CountryConfig:
    country_code: str
    country_name: str
    currency_code: str
    fiscal_year_start: str        # MM-DD
    pay_frequency: str            # MONTHLY | BIWEEKLY | WEEKLY
    tax_brackets: list[TaxBracket] = field(default_factory=list)

    def get_applicable_taxes(
        self,
        annual_income: float,
        employee_type: str,
        state_id: Optional[int] = None,
        city_id: Optional[int] = None,
    ) -> list[TaxBracket]:
        """Return tax brackets that apply to this income and employee type."""
        applicable = []
        for bracket in self.tax_brackets:
            # Filter by employee type
            if bracket.applies_to not in ("ALL", employee_type):
                continue
            # Filter by income band
            if annual_income < bracket.income_from:
                continue
            if bracket.income_to is not None and annual_income > bracket.income_to:
                continue
            applicable.append(bracket)
        return applicable

    def calculate_period_divisor(self) -> int:
        """Return how many pay periods in a year for this country."""
        return {"MONTHLY": 12, "BIWEEKLY": 26, "WEEKLY": 52}.get(self.pay_frequency, 12)


class CountryConfigRegistry:
    """
    Loads and caches country payroll configs from Oracle DB.
    Designed to be extensible — new countries added via DB, not code.
    """

    def __init__(self, connection):
        self._conn = connection
        self._cache: dict[str, CountryConfig] = {}

    def load_all(self) -> dict[str, CountryConfig]:
        """Load all active countries and their tax rules from Oracle."""
        cur = self._conn.cursor()

        # Load countries
        cur.execute("""
            SELECT COUNTRY_CODE, COUNTRY_NAME, CURRENCY_CODE,
                   FISCAL_YEAR_START, PAY_FREQUENCY
            FROM GPS_COUNTRIES
            WHERE ACTIVE = 'Y'
            ORDER BY COUNTRY_CODE
        """)
        countries = {}
        for row in cur.fetchall():
            code = row[0]
            countries[code] = CountryConfig(
                country_code=code,
                country_name=row[1],
                currency_code=row[2],
                fiscal_year_start=row[3],
                pay_frequency=row[4],
            )

        # Load tax rules
        cur.execute("""
            SELECT COUNTRY_CODE, TAX_TYPE, TAX_NAME,
                   EMPLOYEE_RATE, EMPLOYER_RATE,
                   INCOME_FROM, INCOME_TO, APPLIES_TO
            FROM GPS_TAX_RULES
            WHERE ACTIVE = 'Y'
              AND STATE_ID IS NULL
              AND CITY_ID IS NULL
              AND (EFFECTIVE_TO IS NULL OR EFFECTIVE_TO >= SYSDATE)
            ORDER BY COUNTRY_CODE, INCOME_FROM
        """)
        for row in cur.fetchall():
            cc = row[0]
            if cc not in countries:
                continue
            countries[cc].tax_brackets.append(TaxBracket(
                tax_type=row[1],
                tax_name=row[2],
                employee_rate=float(row[3]),
                employer_rate=float(row[4]),
                income_from=float(row[5]),
                income_to=float(row[6]) if row[6] is not None else None,
                applies_to=row[7],
            ))

        self._cache = countries
        return countries

    def get(self, country_code: str) -> CountryConfig:
        if not self._cache:
            self.load_all()
        config = self._cache.get(country_code.upper())
        if not config:
            raise ValueError(f"Country '{country_code}' not found or not active in registry")
        return config

    def list_countries(self) -> list[str]:
        if not self._cache:
            self.load_all()
        return sorted(self._cache.keys())

    def add_country(
        self,
        country_code: str,
        country_name: str,
        currency_code: str,
        fiscal_year_start: str,
        pay_frequency: str,
    ) -> None:
        """
        Register a new country. This is how the system scales to new offices —
        insert a record, the engine picks it up automatically.
        """
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO GPS_COUNTRIES
                (COUNTRY_CODE, COUNTRY_NAME, CURRENCY_CODE, FISCAL_YEAR_START, PAY_FREQUENCY)
            VALUES (:1, :2, :3, :4, :5)
        """, (country_code.upper(), country_name, currency_code.upper(), fiscal_year_start, pay_frequency))
        self._conn.commit()
        self._cache.pop(country_code.upper(), None)  # invalidate cache
        print(f"✅ Country '{country_code}' registered. Add tax rules to GPS_TAX_RULES to complete setup.")
