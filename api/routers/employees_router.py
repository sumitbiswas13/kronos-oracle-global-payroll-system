"""
Employees Router — /employees endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from api.auth import get_current_user, require_manager_or_admin, CurrentUser

router = APIRouter(prefix="/employees", tags=["Employees"])

# Mock data (replace with Oracle queries via OracleHRAdapter)
MOCK_EMPLOYEES = [
    {"employee_id": 1,  "name": "James Carter",   "type": "FULLTIME", "country": "US", "currency": "USD", "salary": 95000,   "kronos_id": "KRN001"},
    {"employee_id": 2,  "name": "Priya Sharma",   "type": "FULLTIME", "country": "IN", "currency": "INR", "salary": 1800000, "kronos_id": "KRN002"},
    {"employee_id": 3,  "name": "Oliver Bennett", "type": "FULLTIME", "country": "GB", "currency": "GBP", "salary": 65000,   "kronos_id": "KRN003"},
    {"employee_id": 4,  "name": "Chloe Thompson", "type": "FULLTIME", "country": "AU", "currency": "AUD", "salary": 95000,   "kronos_id": "KRN004"},
    {"employee_id": 5,  "name": "Marcus Williams","type": "HOURLY",   "country": "US", "currency": "USD", "hourly_rate": 28, "kronos_id": "KRN005"},
    {"employee_id": 6,  "name": "Aisha Patel",    "type": "HOURLY",   "country": "IN", "currency": "INR", "hourly_rate": 450,"kronos_id": "KRN006"},
    {"employee_id": 7,  "name": "Emma Wilson",    "type": "PARTTIME", "country": "GB", "currency": "GBP", "hourly_rate": 18, "kronos_id": "KRN007"},
    {"employee_id": 8,  "name": "Liam Johnson",   "type": "HOURLY",   "country": "AU", "currency": "AUD", "hourly_rate": 35, "kronos_id": "KRN008"},
    {"employee_id": 9,  "name": "Sofia Martinez", "type": "FULLTIME", "country": "US", "currency": "USD", "salary": 110000,  "kronos_id": "KRN009"},
    {"employee_id": 10, "name": "Raj Kumar",      "type": "CONTRACT", "country": "IN", "currency": "INR", "salary": 2400000, "kronos_id": "KRN010"},
]


@router.get("/", summary="List all employees")
def list_employees(
    country: str = None,
    type_code: str = None,
    current_user: CurrentUser = Depends(require_manager_or_admin),
):
    emps = MOCK_EMPLOYEES
    if country:
        emps = [e for e in emps if e["country"] == country.upper()]
    if type_code:
        emps = [e for e in emps if e["type"] == type_code.upper()]
    return {"total": len(emps), "employees": emps}


@router.get("/{employee_id}", summary="Get employee by ID")
def get_employee(
    employee_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    # Employees can only see their own record
    if current_user.role == "EMPLOYEE" and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="You can only view your own record")
    emp = next((e for e in MOCK_EMPLOYEES if e["employee_id"] == employee_id), None)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return emp
