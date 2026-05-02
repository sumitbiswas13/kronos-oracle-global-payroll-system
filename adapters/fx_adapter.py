"""
FX Rates Adapter
Fetches live exchange rates from frankfurter.app (free, no API key needed).
Falls back to cached rates in Oracle if the API is unavailable.
"""

from datetime import date, timedelta
from typing import Optional
import httpx


class FXAdapter:

    BASE_URL = "https://api.frankfurter.app"
    BASE_CURRENCY = "USD"

    def __init__(self, connection=None):
        self._conn = connection  # Optional Oracle connection for caching
        self._cache: dict[tuple, float] = {}

    def get_rate(self, from_currency: str, to_currency: str, rate_date: Optional[date] = None) -> float:
        """
        Get exchange rate from from_currency to to_currency.
        Uses today's rate if no date specified.
        """
        if from_currency == to_currency:
            return 1.0

        rate_date = rate_date or date.today()
        cache_key = (from_currency, to_currency, rate_date)

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try Oracle cache first
        if self._conn:
            cached = self._get_from_oracle(from_currency, to_currency, rate_date)
            if cached:
                self._cache[cache_key] = cached
                return cached

        # Fetch from API
        try:
            rate = self._fetch_from_api(from_currency, to_currency, rate_date)
            self._cache[cache_key] = rate
            if self._conn:
                self._save_to_oracle(from_currency, to_currency, rate, rate_date)
            return rate
        except Exception as e:
            print(f"  ⚠️  FX API unavailable ({e}), using fallback rates")
            return self._fallback_rate(from_currency, to_currency)

    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        rate_date: Optional[date] = None,
    ) -> tuple[float, float]:
        """
        Convert amount from one currency to another.
        Returns (converted_amount, rate_used).
        """
        rate = self.get_rate(from_currency, to_currency, rate_date)
        return round(amount * rate, 2), rate

    def get_rates_for_currencies(
        self,
        currencies: list[str],
        base: str = "USD",
        rate_date: Optional[date] = None,
    ) -> dict[str, float]:
        """Fetch rates for multiple currencies in one API call."""
        rate_date = rate_date or date.today()
        date_str = rate_date.strftime("%Y-%m-%d")
        symbols = ",".join(c for c in currencies if c != base)

        try:
            resp = httpx.get(
                f"{self.BASE_URL}/{date_str}",
                params={"from": base, "to": symbols},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            rates = {base: 1.0}
            rates.update(data.get("rates", {}))
            return rates
        except Exception:
            return {c: self._fallback_rate(base, c) for c in currencies}

    def _fetch_from_api(self, from_currency: str, to_currency: str, rate_date: date) -> float:
        date_str = rate_date.strftime("%Y-%m-%d")
        resp = httpx.get(
            f"{self.BASE_URL}/{date_str}",
            params={"from": from_currency, "to": to_currency},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["rates"][to_currency])

    def _get_from_oracle(self, from_currency: str, to_currency: str, rate_date: date) -> Optional[float]:
        try:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT RATE FROM GPS_FX_RATES
                WHERE FROM_CURRENCY = :fc
                  AND TO_CURRENCY   = :tc
                  AND RATE_DATE     = :rd
            """, {"fc": from_currency, "tc": to_currency, "rd": rate_date})
            row = cur.fetchone()
            return float(row[0]) if row else None
        except Exception:
            return None

    def _save_to_oracle(self, from_currency: str, to_currency: str, rate: float, rate_date: date):
        try:
            cur = self._conn.cursor()
            cur.execute("""
                MERGE INTO GPS_FX_RATES f
                USING (SELECT :fc AS fc, :tc AS tc, :rd AS rd FROM DUAL) src
                ON (f.FROM_CURRENCY = src.fc AND f.TO_CURRENCY = src.tc AND f.RATE_DATE = src.rd)
                WHEN MATCHED THEN UPDATE SET RATE = :rate
                WHEN NOT MATCHED THEN INSERT
                    (FROM_CURRENCY, TO_CURRENCY, RATE, RATE_DATE)
                VALUES (:fc, :tc, :rate, :rd)
            """, {"fc": from_currency, "tc": to_currency, "rate": rate, "rd": rate_date})
            self._conn.commit()
        except Exception:
            pass  # FX caching is best-effort

    def _fallback_rate(self, from_currency: str, to_currency: str) -> float:
        """Approximate fallback rates if API is unavailable."""
        usd_rates = {
            "USD": 1.0, "GBP": 0.79, "EUR": 0.92,
            "INR": 83.5, "AUD": 1.53, "CAD": 1.36,
            "SGD": 1.34, "JPY": 149.5, "BRL": 4.97,
        }
        from_usd = usd_rates.get(from_currency, 1.0)
        to_usd   = usd_rates.get(to_currency, 1.0)
        return round(to_usd / from_usd, 8)
