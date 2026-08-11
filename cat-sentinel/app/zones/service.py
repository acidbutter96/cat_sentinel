from __future__ import annotations

import uuid

from app.core.decorators import log_errors
from app.core.exceptions import NotFoundError
from app.zones.models import Zone
from app.zones.repository import ZoneRepository
from app.zones.schemas import ZoneCreate, ZoneUpdate


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test.

    `polygon` is a list of (x, y) vertices (open ring -- no need to repeat
    the first point at the end). Pure function, no I/O, so it's directly
    unit-testable without a database or HTTP client.
    """
    x, y = point
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    x1, y1 = polygon[0]
    for i in range(1, n + 1):
        x2, y2 = polygon[i % n]
        if y > min(y1, y2) and y <= max(y1, y2) and x <= max(x1, x2) and y1 != y2:
            x_intersect = (y - y1) * (x2 - x1) / (y2 - y1) + x1
            if x1 == x2 or x <= x_intersect:
                inside = not inside
        x1, y1 = x2, y2
    return inside


@log_errors
class ZoneService:
    def __init__(self, repository: ZoneRepository):
        self.repository = repository

    async def create(self, payload: ZoneCreate) -> Zone:
        return await self.repository.create(payload)

    async def get(self, zone_id: uuid.UUID) -> Zone:
        zone = await self.repository.get(zone_id)
        if zone is None:
            raise NotFoundError(f"Zone {zone_id} not found")
        return zone

    async def list(self, limit: int = 50, offset: int = 0) -> list[Zone]:
        return await self.repository.list(limit=limit, offset=offset)

    async def list_active_for_camera(self, camera_id: str) -> list[Zone]:
        return await self.repository.list_active_for_camera(camera_id)

    async def update(self, zone_id: uuid.UUID, payload: ZoneUpdate) -> Zone:
        zone = await self.get(zone_id)
        return await self.repository.update(zone, payload)

    async def delete(self, zone_id: uuid.UUID) -> None:
        zone = await self.get(zone_id)
        await self.repository.delete(zone)
