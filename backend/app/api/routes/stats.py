"""GET /api/v1/admin/stats: the numbers on the admin dashboard."""

from fastapi import APIRouter

from app.api.deps import DbSession, StaffOrAdmin
from app.schemas.stats import DashboardStats
from app.services import stats as service

router = APIRouter(prefix="/admin", tags=["dashboard (admin)"], dependencies=[StaffOrAdmin])


@router.get("/stats")
def dashboard_stats(db: DbSession) -> DashboardStats:
    return DashboardStats.model_validate(service.dashboard(db))
