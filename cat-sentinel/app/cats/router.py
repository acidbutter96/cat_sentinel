import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.cats.repository import CatRepository
from app.cats.schemas import CatRead, CatUpdate
from app.cats.service import CatService
from app.core.dependencies import DbSession, PaginationDep

router = APIRouter(prefix="/detected-cats", tags=["detected-cats"])


def get_cat_service(db: DbSession) -> CatService:
    return CatService(CatRepository(db))


CatServiceDep = Annotated[CatService, Depends(get_cat_service)]


@router.get("/", response_model=list[CatRead], summary="List detected cat identities")
async def list_cats(service: CatServiceDep, pagination: PaginationDep) -> list[CatRead]:
    cats = await service.list(limit=pagination.limit, offset=pagination.offset)
    return [CatRead.model_validate(c) for c in cats]


@router.get("/{cat_id}", response_model=CatRead, summary="Get a detected cat identity")
async def get_cat(cat_id: uuid.UUID, service: CatServiceDep) -> CatRead:
    cat = await service.get(cat_id)
    return CatRead.model_validate(cat)


@router.patch("/{cat_id}", response_model=CatRead, summary="Update a detected cat identity")
async def update_cat(cat_id: uuid.UUID, payload: CatUpdate, service: CatServiceDep) -> CatRead:
    cat = await service.update(cat_id, payload)
    return CatRead.model_validate(cat)
