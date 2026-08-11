from app.zones.service import point_in_polygon

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


def test_point_inside_square_is_inside():
    assert point_in_polygon((5.0, 5.0), SQUARE) is True


def test_point_outside_square_is_outside():
    assert point_in_polygon((15.0, 15.0), SQUARE) is False


def test_point_far_outside_is_outside():
    assert point_in_polygon((-5.0, 5.0), SQUARE) is False


def test_triangle_containment():
    triangle = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]
    assert point_in_polygon((5.0, 5.0), triangle) is True
    assert point_in_polygon((9.0, 9.0), triangle) is False


def test_degenerate_polygon_with_fewer_than_three_points_is_never_inside():
    assert point_in_polygon((1.0, 1.0), [(0.0, 0.0), (1.0, 1.0)]) is False
