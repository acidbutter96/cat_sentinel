from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

# Cross-domain DI only -- db session, pagination. Domain-specific providers
# (e.g. ZoneServiceDep) live in that domain's own router.py.

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


class Pagination:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        self.limit = limit
        self.offset = offset


PaginationDep = Annotated[Pagination, Depends(Pagination)]
