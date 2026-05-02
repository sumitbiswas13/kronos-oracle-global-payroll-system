"""
Phase 2 Demo — Kronos adapter + Oracle HR adapter + FX adapter.
No live Oracle or Kronos connection required.
Run with: python demo_phase2.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from adapters.kronos_adapter import MockKronosAdapter
from adapters.fx_adapter import FXAdapter

# ── 1. Kronos Adapter Demo ────────────────────────────────────
print("=" * 65)
print("  Global Payroll System — Phase 2 Demo")
print("  Kronos Adapter + FX Adapter")
print("=" * 65)

kronos = MockKronosAdapter()

print("\n📋 KRONOS: All employees")
print(f"  {'ID':<8} {'Name':<22} {'Location':<10} {'Pay Rule':<10}")
print(f"  {'─'*8} {'─'*22} {'─'*10} {'─'*10}")
for emp in kronos.get_all_employees():
    print(f"  {emp.kronos_id:<8} {emp.first_name+' '+emp.last_name:<22} {emp.location_code:<10} {emp.pay_rule:<10}")

# ── 2. Timecard pull ──────────────────────────────────────────
period_start = date(2024, 11, 1)
period_end   = date(2024, 11, 30)

print(f"\n⏱️  KRONOS: Timecards for {period_start} → {period_end}")
print(f"  {'Employee':<22} {'Regular':>9} {'Overtime':>9} {'PTO':>6} {'Sick':>6} {'Total':>8} {'Approved'}")
print(f"  {'─'*22} {'─'*9} {'─'*9} {'─'*6} {'─'*6} {'─'*8} {'─'*8}")

timecards = kronos.get_timecards_for_period(period_start, period_end)
for tc in timecards:
    emp = kronos.get_employee(tc.employee_id)
    name = f"{emp.first_name} {emp.last_name}"
    approved = "✓" if tc.approved else "✗"
    print(f"  {name:<22} {tc.regular_hours:>9.1f} {tc.overtime_hours:>9.1f} {tc.pto_hours:>6.1f} {tc.sick_hours:>6.1f} {tc.total_hours:>8.1f} {approved:>8}")

# ── 3. Single employee timecard detail ────────────────────────
print(f"\n🔍 KRONOS: Timecard detail for Marcus Williams (KRN005 — Hourly)")
tc = kronos.get_timecard("KRN005", period_start, period_end)
print(f"  Regular hours  : {tc.regular_hours}")
print(f"  Overtime hours : {tc.overtime_hours}")
print(f"  PTO hours      : {tc.pto_hours}")
print(f"  Total hours    : {tc.total_hours}")
print(f"  Shifts worked  : {len(tc.shifts)}")
print(f"  Approved       : {tc.approved} by {tc.approved_by}")
print(f"\n  First 3 shifts:")
for s in tc.shifts[:3]:
    ot = " [OT]" if s.is_overtime else ""
    print(f"    {s.shift_date}  {s.hours_worked}h{ot}")

# ── 4. FX Rates ───────────────────────────────────────────────
print(f"\n💱 FX ADAPTER: Exchange rates (fallback mode)")
fx = FXAdapter()  # no Oracle connection in demo
currencies = ["USD", "GBP", "INR", "AUD"]
print(f"\n  Converting 10,000 units to USD:")
print(f"  {'From':<6} {'Amount':>12} {'Rate':>12} {'USD Value':>12}")
print(f"  {'─'*6} {'─'*12} {'─'*12} {'─'*12}")
for currency in currencies:
    converted, rate = fx.convert(10000, currency, "USD")
    print(f"  {currency:<6} {10000:>12,.2f} {rate:>12.6f} {converted:>12,.2f}")

# ── 5. Sync simulation ────────────────────────────────────────
print(f"\n🔄 ORACLE SYNC SIMULATION (mock — no live DB)")
print(f"  Would sync {len(kronos.get_all_employees())} Kronos employees to GPS_EMPLOYEES")

pay_rule_map = {
    "SALARIED": ("FULLTIME",  85000.0, None),
    "HOURLY":   ("HOURLY",    None,    25.0),
    "PARTTIME": ("PARTTIME",  None,    18.0),
    "CONTRACT": ("CONTRACT",  None,    None),
}
for emp in kronos.get_all_employees():
    type_code, salary, rate = pay_rule_map.get(emp.pay_rule, ("FULLTIME", None, None))
    pay_info = f"salary=${salary:,.0f}" if salary else f"rate=${rate}/hr" if rate else "TBD"
    print(f"  {emp.kronos_id} → {emp.first_name} {emp.last_name:<18} type={type_code:<10} {pay_info}")

print(f"\n✅ Phase 2 complete! Kronos + FX adapters ready.")
print(f"   Next: Phase 3 — Payroll calculation engine\n")
