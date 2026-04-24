"""
main.py — FinSight AI FastAPI entry point
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import uuid

from core.config import get_settings
from core.auth import hash_password, verify_password, create_access_token, get_current_user
from models.database import get_db, User, Report
from tasks.report_task import generate_report

settings = get_settings()

app = FastAPI(
    title="FinSight AI",
    description="AI-powered financial intelligence report generator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    tier: str


class GenerateReportRequest(BaseModel):
    asset_type: str        # "commodity" | "equity"
    asset_symbol: str
    analysis_type: str = "full"


class ReportStatusResponse(BaseModel):
    id: str
    asset_type: str
    asset_symbol: str
    status: str
    file_url: Optional[str]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]


# ── Health ─────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "service": "FinSight AI", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ── Auth ───────────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        tier="free",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, tier=user.tier)


@app.post("/auth/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, tier=user.tier)


@app.get("/auth/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id":         current_user.id,
        "email":      current_user.email,
        "full_name":  current_user.full_name,
        "tier":       current_user.tier,
        "created_at": current_user.created_at.isoformat(),
    }


# ── Reports ────────────────────────────────────────────────────

TIER_LIMITS = {"free": 3, "basic": 20, "pro": 100, "business": 999999}
VALID_ASSET_TYPES = {"commodity", "equity"}


@app.post("/reports/generate")
async def generate(
    body: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(400, f"Invalid asset_type. Choose: {VALID_ASSET_TYPES}")

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count(Report.id)).where(
            Report.user_id    == current_user.id,
            Report.created_at >= month_start,
        )
    )
    monthly_count = count_result.scalar() or 0
    limit = TIER_LIMITS.get(current_user.tier, 3)

    if monthly_count >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Monthly limit of {limit} reports reached for {current_user.tier} tier.",
        )

    report_id = str(uuid.uuid4())
    report = Report(
        id=report_id,
        user_id=current_user.id,
        asset_type=body.asset_type,
        asset_symbol=body.asset_symbol.upper(),
        analysis_type=body.analysis_type,
        status="queued",
    )
    db.add(report)
    await db.flush()   # get the record in DB before queuing task

    # Queue task THEN save task id — single commit
    task = generate_report.delay(
        report_id,
        body.asset_type,
        body.asset_symbol.upper(),
        body.analysis_type,
        current_user.id,
    )
    report.celery_task_id = task.id
    await db.commit()

    return {
        "report_id": report_id,
        "status":    "queued",
        "message":   "Report generation started. Poll /reports/{id} for status.",
        "task_id":   task.id,
    }


@app.get("/reports/{report_id}", response_model=ReportStatusResponse)
async def get_report_status(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    return ReportStatusResponse(
        id=report.id,
        asset_type=report.asset_type,
        asset_symbol=report.asset_symbol,
        status=report.status,
        file_url=report.file_url,
        error_message=report.error_message,
        created_at=report.created_at.isoformat(),
        completed_at=report.completed_at.isoformat() if report.completed_at else None,
    )


@app.get("/reports")
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .limit(50)
    )
    reports = result.scalars().all()
    return {
        "reports": [
            {
                "id":           r.id,
                "asset_type":   r.asset_type,
                "asset_symbol": r.asset_symbol,
                "status":       r.status,
                "file_url":     r.file_url,
                "created_at":   r.created_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in reports
        ],
        "total": len(reports),
    }


@app.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    await db.delete(report)
    await db.commit()
    return {"message": "Report deleted"}