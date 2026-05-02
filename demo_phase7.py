"""
Phase 7 Demo — Leave Tracker + Bonus & Deductions Engine
Run with: python demo_phase7.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from engine.leave_tracker import LeaveTracker, LeaveStatus, COUNTRY_ENTITLEMENTS
from engine.bonus_deduction_engine import BonusDeductionEngine, BonusRule, BonusType, STANDARD_DEDUCTION_RULES

print("=" * 65)
print("  Global Payroll System — Phase 7 Demo")
print("  Leave Tracker + Bonus & Deductions Engine")
print("=" * 65)

tracker = LeaveTracker()
bd      = BonusDeductionEngine()

# ── 1. Initialise leave balances ──────────────────────────────
print("\n📋 LEAVE TRACKER: Initialising employees for 2024\n")
countries = {"James Carter (US)": (1,"US"), "Oliver Bennett (GB)": (3,"GB"),
             "Priya Sharma (IN)":  (2,"IN"), "Chloe Thompson (AU)": (4,"AU")}

for name, (emp_id, cc) in countries.items():
    balances = tracker.initialise_employee(emp_id, cc, 2024)
    annual   = next((b for b in balances if b.leave_code == "ANNUAL"), None)
    sick     = next((b for b in balances if b.leave_code == "SICK"), None)
    print(f"  {name:<28} Annual: {annual.entitled_days:.0f}d  Sick: {sick.entitled_days:.0f}d")

# ── 2. Submit and approve requests ────────────────────────────
print("\n📅 LEAVE REQUESTS: Submit and approve\n")
r1 = tracker.request_leave(1, "ANNUAL", date(2024,12,23), date(2024,12,27), "Christmas break")
r2 = tracker.request_leave(1, "SICK",   date(2024,10,15), date(2024,10,15), "Unwell")
r3 = tracker.request_leave(3, "ANNUAL", date(2024,8,5),   date(2024,8,16),  "Summer holiday")
r4 = tracker.request_leave(2, "ANNUAL", date(2024,11,1),  date(2024,11,5),  "Diwali")

print(f"  Submitted {4} leave requests")

tracker.approve_request(r1.request_id, approved_by=99)
tracker.approve_request(r2.request_id, approved_by=99)
tracker.approve_request(r3.request_id, approved_by=99)
tracker.reject_request( r4.request_id, approved_by=99, reason="Payroll period — please rebook")

print(f"  Approved: {r1.days_requested:.0f}d Christmas, {r2.days_requested:.0f}d sick, {r3.days_requested:.0f}d summer holiday")
print(f"  Rejected: {r4.days_requested:.0f}d Diwali — {r4.rejection_reason}")

# ── 3. Balance summary ────────────────────────────────────────
print("\n📊 LEAVE BALANCES: James Carter (US) after requests\n")
print(f"  {'Leave type':<20} {'Entitled':>9} {'Taken':>7} {'Pending':>9} {'Remaining':>10}")
print(f"  {'─'*20} {'─'*9} {'─'*7} {'─'*9} {'─'*10}")
for b in tracker.get_all_balances(1, 2024):
    if b.entitled_days > 0:
        print(f"  {b.leave_code:<20} {b.entitled_days:>9.1f} {b.taken_days:>7.1f} {b.pending_days:>9.1f} {b.remaining_days:>10.1f}")

# ── 4. Year-end carryover ─────────────────────────────────────
print("\n🔄 YEAR-END CARRYOVER: Initialising 2025 and carrying over\n")
tracker.initialise_employee(1, "US", 2025)
carried = tracker.carry_over_balances(1, 2024)
for code, days in carried:
    print(f"  {code}: {days} days carried into 2025")

# ── 5. Deductions ─────────────────────────────────────────────
print("\n💰 BONUS & DEDUCTIONS ENGINE\n")
print("  Standard deductions — US FULLTIME employee, $3,653.85 gross:\n")
deds = bd.get_standard_deductions("US", "FULLTIME", 3653.85)
for d in deds:
    print(f"  {'Pre-tax' if d.is_pre_tax else 'Post-tax':<10} {d.description:<30} USD {d.amount:>8.2f}")

print("\n  Standard deductions — UK FULLTIME employee, £5,416.67 gross:\n")
deds_uk = bd.get_standard_deductions("GB", "FULLTIME", 5416.67)
for d in deds_uk:
    print(f"  {'Pre-tax' if d.is_pre_tax else 'Post-tax':<10} {d.description:<30} GBP {d.amount:>8.2f}")

# ── 6. Bonuses ────────────────────────────────────────────────
print("\n🎁 BONUSES\n")
print("  Performance bonus — James Carter, rating 4.2/5.0, 10% target:\n")
perf = bd.calculate_performance_bonus(
    annual_salary=95000, performance_rating=4.2,
    target_bonus_pct=0.10, tax_rate=0.22, currency="USD"
)
print(f"  Gross bonus : USD {perf.gross_amount:,.2f}")
print(f"  Tax (22%)   : USD {perf.tax_amount:,.2f}")
print(f"  Net bonus   : USD {perf.net_amount:,.2f}")

print("\n  India statutory annual bonus (8.33% of salary):\n")
india_bonuses = bd.get_country_bonuses("IN", "FULLTIME", 1800000, 150000, 0.30, "INR")
for b in india_bonuses:
    print(f"  {b.description:<40} INR {b.gross_amount:>12,.2f} (net: {b.net_amount:>12,.2f})")

print(f"\n✅ Phase 7 complete! Leave tracker + bonus/deductions engine ready.")
print(f"   Next: Phase 8 — Demo data polish + README update\n")
