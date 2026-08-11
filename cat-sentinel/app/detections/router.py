import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSession, PaginationDep
from app.detections.repository import DetectionRepository
from app.detections.schemas import DetectionRead
from app.detections.service import DetectionService

router = APIRouter(prefix="/detections", tags=["detections"])


def get_detection_service(db: DbSession) -> DetectionService:
    return DetectionService(DetectionRepository(db))


DetectionServiceDep = Annotated[DetectionService, Depends(get_detection_service)]


@router.get("/", response_model=list[DetectionRead], summary="List detections")
async def list_detections(
    service: DetectionServiceDep,
    pagination: PaginationDep,
    cat_id: Annotated[uuid.UUID | None, Query()] = None,
    in_danger_zone: Annotated[bool | None, Query()] = None,
) -> list[DetectionRead]:
    detections = await service.list(
        limit=pagination.limit,
        offset=pagination.offset,
        cat_id=cat_id,
        in_danger_zone=in_danger_zone,
    )
    return [DetectionRead.model_validate(d) for d in detections]
