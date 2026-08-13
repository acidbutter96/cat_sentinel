import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.core.dependencies import DbSession, PaginationDep
from app.registered_cats.photos import MAX_PHOTO_BYTES, resolve_photo, save_photo
from app.registered_cats.repository import RegisteredCatRepository
from app.registered_cats.schemas import RegisteredCatCreate, RegisteredCatRead, RegisteredCatUpdate
from app.registered_cats.service import RegisteredCatService

router = APIRouter(prefix="/cats", tags=["registered-cats"])


def get_service(db: DbSession) -> RegisteredCatService:
    return RegisteredCatService(RegisteredCatRepository(db))


ServiceDep = Annotated[RegisteredCatService, Depends(get_service)]


@router.post("/", response_model=RegisteredCatRead, status_code=status.HTTP_201_CREATED)
async def create_cat(payload: RegisteredCatCreate, service: ServiceDep) -> RegisteredCatRead:
    return RegisteredCatRead.model_validate(await service.create(payload))


@router.get("/", response_model=list[RegisteredCatRead])
async def list_cats(service: ServiceDep, pagination: PaginationDep) -> list[RegisteredCatRead]:
    cats = await service.list(pagination.limit, pagination.offset)
    return [RegisteredCatRead.model_validate(cat) for cat in cats]


@router.get("/{cat_id}/photo", summary="Get a registered cat profile image")
async def get_cat_photo(cat_id: uuid.UUID, service: ServiceDep) -> FileResponse:
    cat = await service.get(cat_id)
    if cat.photo_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cat photo not found")
    try:
        path = resolve_photo(cat.photo_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cat photo not found",
        ) from exc
    return FileResponse(path)


async def _store_reference_image(
    cat_id: uuid.UUID, request: Request, service: ServiceDep
) -> RegisteredCatRead:
    await service.get(cat_id)
    content_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0]
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_PHOTO_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Image exceeds 5 MB",
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content length",
            ) from exc
    image_bytes = await request.body()
    try:
        photo_path, embedding = await asyncio.to_thread(
            save_photo, cat_id, content_type, image_bytes
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return RegisteredCatRead.model_validate(
        await service.add_reference_image(cat_id, photo_path, embedding)
    )


@router.post(
    "/{cat_id}/images",
    response_model=RegisteredCatRead,
    summary="Upload a cat reference image",
)
async def upload_cat_reference_image(
    cat_id: uuid.UUID, request: Request, service: ServiceDep
) -> RegisteredCatRead:
    return await _store_reference_image(cat_id, request, service)


@router.put(
    "/{cat_id}/photo",
    response_model=RegisteredCatRead,
    summary="Upload a cat profile image",
)
async def upload_cat_photo(
    cat_id: uuid.UUID, request: Request, service: ServiceDep
) -> RegisteredCatRead:
    return await _store_reference_image(cat_id, request, service)


@router.get("/{cat_id}", response_model=RegisteredCatRead)
async def get_cat(cat_id: uuid.UUID, service: ServiceDep) -> RegisteredCatRead:
    return RegisteredCatRead.model_validate(await service.get(cat_id))


@router.patch("/{cat_id}", response_model=RegisteredCatRead)
async def update_cat(
    cat_id: uuid.UUID, payload: RegisteredCatUpdate, service: ServiceDep
) -> RegisteredCatRead:
    return RegisteredCatRead.model_validate(await service.update(cat_id, payload))
