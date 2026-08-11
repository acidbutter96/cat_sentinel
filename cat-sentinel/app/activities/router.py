from typing import Annotated

from fastapi import APIRouter, Depends

from app.activities.repository import ActivityRepository
from app.activities.schemas import ActivityRead
from app.activities.service import ActivityService
from app.core.dependencies import DbSession, PaginationDep

router = APIRouter(prefix="/activities", tags=["activities"])


def get_activity_service(db: DbSession) -> ActivityService:
    return ActivityService(ActivityRepository(db))


ActivityServiceDep = Annotated[ActivityService, Depends(get_activity_service)]


@router.get("/", response_model=list[ActivityRead], summary="List activity timeline entries")
async def list_activities(
    service: ActivityServiceDep, pagination: PaginationDep
) -> list[ActivityRead]:
    activities = await service.list(limit=pagination.limit, offset=pagination.offset)
    return [ActivityRead.model_validate(a) for a in activities]
