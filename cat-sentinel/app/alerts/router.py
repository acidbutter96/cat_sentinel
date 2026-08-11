from typing import Annotated

from fastapi import APIRouter, Depends

from app.alerts.repository import AlertRepository
from app.alerts.schemas import AlertRead
from app.alerts.service import AlertService
from app.core.dependencies import DbSession, PaginationDep

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_alert_service(db: DbSession) -> AlertService:
    return AlertService(AlertRepository(db))


AlertServiceDep = Annotated[AlertService, Depends(get_alert_service)]


@router.get("/", response_model=list[AlertRead], summary="List fired alerts")
async def list_alerts(service: AlertServiceDep, pagination: PaginationDep) -> list[AlertRead]:
    alerts = await service.list(limit=pagination.limit, offset=pagination.offset)
    return [AlertRead.model_validate(a) for a in alerts]
