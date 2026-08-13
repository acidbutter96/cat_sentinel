from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.settings.config import settings

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


def resolve_snapshot_path(snapshot_path: str) -> Path:
    """Resolve a DB path while preventing access outside SNAPSHOT_DIR."""
    root = Path(settings.snapshot_dir).resolve()
    requested = Path(snapshot_path)
    candidates = [Path.cwd() / requested, root / requested]

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved == root or root in resolved.parents:
            return resolved
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")


@router.get("", summary="Serve a stored cat snapshot")
async def get_snapshot(
    path: str = Query(min_length=1, description="Relative snapshot_path stored in detections")
) -> FileResponse:
    resolved = resolve_snapshot_path(path)
    if not resolved.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    return FileResponse(resolved, media_type="image/jpeg")
