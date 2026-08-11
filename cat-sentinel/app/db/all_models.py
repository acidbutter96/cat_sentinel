"""Imports every domain's models module so Base.metadata sees every table.

Used by alembic/env.py for autogenerate, and by tests that build the schema
without going through app.main. A domain added without being imported here
will silently be invisible to `alembic revision --autogenerate`.
"""

from app.activities import models as activities_models  # noqa: F401
from app.alerts import models as alerts_models  # noqa: F401
from app.cats import models as cats_models  # noqa: F401
from app.detections import models as detections_models  # noqa: F401
from app.zones import models as zones_models  # noqa: F401
