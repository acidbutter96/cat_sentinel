from app.zones.schemas import Point, ZoneCreate


def make_zone_payload(**overrides) -> dict:
    defaults = {
        "camera_id": "cam-1",
        "name": "terrarium-perimeter",
        "points": [{"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 0.0}, {"x": 10.0, "y": 10.0}],
        "is_active": True,
    }
    return {**defaults, **overrides}


def make_zone_create(**overrides) -> ZoneCreate:
    payload = make_zone_payload(**overrides)
    payload["points"] = [Point(**p) for p in payload["points"]]
    return ZoneCreate(**payload)
