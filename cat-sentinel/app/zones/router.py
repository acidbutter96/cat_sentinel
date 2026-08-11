import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import DbSession, PaginationDep
from app.zones.repository import ZoneRepository
from app.zones.schemas import ZoneCreate, ZoneRead, ZoneUpdate
from app.zones.service import ZoneService

router = APIRouter(prefix="/zones", tags=["zones"])


def get_zone_service(db: DbSession) -> ZoneService:
    return ZoneService(ZoneRepository(db))


ZoneServiceDep = Annotated[ZoneService, Depends(get_zone_service)]


@router.get("/", response_model=list[ZoneRead], summary="List zones")
async def list_zones(service: ZoneServiceDep, pagination: PaginationDep) -> list[ZoneRead]:
    zones = await service.list(limit=pagination.limit, offset=pagination.offset)
    return [ZoneRead.model_validate(z) for z in zones]


@router.post(
    "/", response_model=ZoneRead, status_code=status.HTTP_201_CREATED, summary="Create a zone"
)
async def create_zone(payload: ZoneCreate, service: ZoneServiceDep) -> ZoneRead:
    zone = await service.create(payload)
    return ZoneRead.model_validate(zone)


@router.get("/{zone_id}", response_model=ZoneRead, summary="Get a zone")
async def get_zone(zone_id: uuid.UUID, service: ZoneServiceDep) -> ZoneRead:
    zone = await service.get(zone_id)
    return ZoneRead.model_validate(zone)


@router.patch("/{zone_id}", response_model=ZoneRead, summary="Update a zone")
async def update_zone(zone_id: uuid.UUID, payload: ZoneUpdate, service: ZoneServiceDep) -> ZoneRead:
    zone = await service.update(zone_id, payload)
    return ZoneRead.model_validate(zone)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a zone")
async def delete_zone(zone_id: uuid.UUID, service: ZoneServiceDep) -> None:
    await service.delete(zone_id)
