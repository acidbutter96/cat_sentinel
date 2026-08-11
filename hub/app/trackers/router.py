from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_cat_sentinel_control_client
from app.trackers.schemas import TrackerRead
from app.trackers.service import TrackerService

router = APIRouter(tags=["trackers"])


# Domain-specific DI provider -- lives here, not in core/dependencies.py,
# since it imports from this domain's own service module.
def get_tracker_service(
    control_client: Annotated[httpx.AsyncClient, Depends(get_cat_sentinel_control_client)],
) -> TrackerService:
    return TrackerService(control_client)


TrackerServiceDep = Annotated[TrackerService, Depends(get_tracker_service)]


@router.get(
    "/trackers",
    response_model=list[TrackerRead],
    status_code=status.HTTP_200_OK,
    summary="List the most recent bounding box for every actively-tracked cat",
)
async def list_trackers(service: TrackerServiceDep) -> list[TrackerRead]:
    return await service.list_active_trackers()
