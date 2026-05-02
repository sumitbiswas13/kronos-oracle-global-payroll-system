"""
Global Payroll System — FastAPI App
Run with: uvicorn api.app:app --reload
Docs at:  http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers.auth_router import router as auth_router
from api.routers.employees_router import router as employees_router
from api.routers.payroll_router import router as payroll_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Global Payroll System API starting...")
    print("📖 Docs: http://localhost:8000/docs")
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="Global Payroll System API",
    description="""
## Global Payroll System — Kronos + Oracle

Enterprise-grade payroll API supporting multiple countries, currencies, and employee types.

### Authentication
All endpoints require a JWT token. Get one via `POST /auth/login`.

**Demo credentials:**
| Email | Password | Role |
|-------|----------|------|
| admin@acme.com | admin123 | ADMIN |
| manager@acme.com | manager123 | MANAGER |
| jcarter@acme.com | emp123 | EMPLOYEE |

### Roles
- **ADMIN** — full access, can trigger payroll runs
- **MANAGER** — read access to all employees and payslips
- **EMPLOYEE** — can only view their own payslip and profile
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(payroll_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "system":  "Global Payroll System",
        "version": "1.0.0",
        "status":  "running",
        "docs":    "/docs",
        "phases_complete": ["Phase 1: Oracle Schema", "Phase 2: Kronos + FX Adapters",
                            "Phase 3: Payroll Engine", "Phase 4: PDF Payslips",
                            "Phase 5: FastAPI + JWT Auth"],
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
