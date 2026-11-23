"""Controller outline geometry with no Maya or Qt dependency."""
import math


SHAPE_NAMES = (
    "Circle", "Square", "Triangle", "Box", "Arrow", "Bidirectional Arrow", "Cross", "Locator",
    "Pole Vector", "Roll", "Foot", "Global", "FK Control", "IK Control",
    "Slider", "Stretch",
)
PLANES = ("XY", "XZ", "YZ")
ICON_FILES = {
    "Circle": "circle.svg",
    "Square": "square.svg",
    "Triangle": "triangle.svg",
    "Box": "box.svg",
    "Arrow": "arrow.svg",
    "Bidirectional Arrow": "bidirectional_arrow.svg",
    "Cross": "cross.svg",
    "Locator": "locator.svg",
    "Pole Vector": "pole_vector.svg",
    "Roll": "roll.svg",
    "Foot": "foot.svg",
    "Global": "global.svg",
    "FK Control": "fk_control.svg",
    "IK Control": "ik_control.svg",
    "Slider": "slider.svg",
    "Stretch": "stretch.svg",
}
SHAPE_DESCRIPTIONS = {
    "Circle": "General rotation or round control",
    "Square": "Simple box-shaped control",
    "Triangle": "Directional or selector control",
    "Box": "Three-dimensional root or body control",
    "Arrow": "One-way direction and aim control",
    "Bidirectional Arrow": "Two-way direction, stretch, and translation control",
    "Cross": "Three-axis alignment control",
    "Locator": "Compact position marker",
    "Pole Vector": "Knee or elbow IK pole vector control",
    "Roll": "Circular rotation and foot-roll control",
    "Foot": "Foot and ankle control outline",
    "Global": "Large master or global rig control",
    "FK Control": "Three-axis FK rotation control",
    "IK Control": "Square IK handle control",
    "Slider": "Horizontal attribute or space slider",
    "Stretch": "Limb length and stretch control",
}


def _plane_point(x, y, plane):
    if plane == "XY":
        return (x, y, 0.0)
    if plane == "XZ":
        return (x, 0.0, y)
    if plane == "YZ":
        return (0.0, x, y)
    raise ValueError("Plane must be XY, XZ, or YZ")


def _scaled(points, size, plane):
    return [_plane_point(x * size, y * size, plane) for x, y in points]


def _ring(radius, size, plane, start=0.0, end=2.0 * math.pi, count=48, center=(0, 0)):
    points = [(center[0] + radius * math.cos(start + (end - start) * i / count),
               center[1] + radius * math.sin(start + (end - start) * i / count))
              for i in range(count + 1)]
    return _scaled(points, size, plane)


def _arrow_head(tip, direction, size, plane, length=0.12, half_width=0.075):
    dx, dy = direction
    magnitude = math.hypot(dx, dy)
    dx, dy = dx / magnitude, dy / magnitude
    base = (tip[0] - dx * length, tip[1] - dy * length)
    normal = (-dy * half_width, dx * half_width)
    return _scaled([tip, (base[0] + normal[0], base[1] + normal[1]),
                    (base[0] - normal[0], base[1] - normal[1]), tip], size, plane)


def _square(size, plane, half=0.5):
    return _scaled([(-half, -half), (half, -half), (half, half),
                    (-half, half), (-half, -half)], size, plane)


def segments(shape, size=2.0, plane="XY"):
    """Return local-space polylines for a named controller outline."""
    try:
        size = float(size)
    except (TypeError, ValueError):
        raise ValueError("Size must be a positive number")
    if not math.isfinite(size) or size <= 0:
        raise ValueError("Size must be a positive number")
    if plane not in PLANES:
        raise ValueError("Plane must be XY, XZ, or YZ")

    if shape == "Circle":
        return [_ring(.5, size, plane, count=64)]
    if shape == "Square":
        return [_square(size, plane)]
    if shape == "Triangle":
        return [_scaled([(0, .5), (.5, -.4), (-.5, -.4), (0, .5)], size, plane)]
    if shape == "Arrow":
        return [_scaled([(-.5, -.12), (.18, -.12), (.18, -.32),
                         (.5, 0), (.18, .32), (.18, .12), (-.5, .12),
                         (-.5, -.12)], size, plane)]
    if shape == "Bidirectional Arrow":
        return [_scaled([(-.5, 0), (-.28, .22), (-.28, .11),
                         (.28, .11), (.28, .22), (.5, 0),
                         (.28, -.22), (.28, -.11), (-.28, -.11),
                         (-.28, -.22), (-.5, 0)], size, plane)]
    if shape == "Box":
        cube = [
            [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5), (-.5, -.5, -.5)],
            [(-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5), (-.5, -.5, .5)],
            [(-.5, -.5, -.5), (-.5, -.5, .5)], [(.5, -.5, -.5), (.5, -.5, .5)],
            [(.5, .5, -.5), (.5, .5, .5)], [(-.5, .5, -.5), (-.5, .5, .5)],
        ]
        return [[tuple(axis * size for axis in point) for point in line] for line in cube]
    if shape == "Cross":
        return [[(-.5 * size, 0, 0), (.5 * size, 0, 0)],
                [(0, -.5 * size, 0), (0, .5 * size, 0)],
                [(0, 0, -.5 * size), (0, 0, .5 * size)]]
    if shape == "Locator":
        return [_scaled([(-.5, 0), (-.13, 0)], size, plane),
                _scaled([(.13, 0), (.5, 0)], size, plane),
                _scaled([(0, -.5), (0, -.13)], size, plane),
                _scaled([(0, .13), (0, .5)], size, plane),
                _ring(.13, size, plane, count=24)]
    if shape == "Pole Vector":
        outline = _scaled([(-.4, .12), (0, .5), (.4, .12), (0, -.5), (-.4, .12)], size, plane)
        stem = _scaled([(0, -.22), (0, .16)], size, plane)
        center = _ring(.055, size, plane, count=16)
        return [outline, stem, center]
    if shape == "Roll":
        arc = _ring(.39, size, plane, start=math.radians(35),
                    end=math.radians(325), count=44)
        tip_angle = math.radians(325)
        tip = (.39 * math.cos(tip_angle), .39 * math.sin(tip_angle))
        tangent = (-math.sin(tip_angle), math.cos(tip_angle))
        return [arc, _arrow_head(tip, tangent, size, plane, .14, .09)]
    if shape == "Foot":
        outline = [(-.16, -.5), (.16, -.5), (.18, -.23), (.25, -.02),
                   (.32, .18), (.34, .32), (.27, .44), (.19, .39),
                   (.12, .5), (.04, .43), (-.04, .5), (-.12, .42),
                   (-.2, .45), (-.29, .33), (-.27, .15), (-.2, -.08),
                   (-.16, -.5)]
        return [_scaled(outline, size, plane)]
    if shape == "Global":
        lines = [_ring(.31, size, plane, count=48)]
        lines.extend([
            _scaled([(0, .30), (0, .5)], size, plane),
            _scaled([(0, -.30), (0, -.5)], size, plane),
            _scaled([(.30, 0), (.5, 0)], size, plane),
            _scaled([(-.30, 0), (-.5, 0)], size, plane),
            _arrow_head((0, .5), (0, 1), size, plane, .12, .08),
            _arrow_head((0, -.5), (0, -1), size, plane, .12, .08),
            _arrow_head((.5, 0), (1, 0), size, plane, .12, .08),
            _arrow_head((-.5, 0), (-1, 0), size, plane, .12, .08),
        ])
        return lines
    if shape == "FK Control":
        xy = _ring(.43, size, "XY", count=48)
        xz = [(x, 0.0, z) for x, _, z in _ring(.43, size, "XZ", count=48)]
        yz = [(0.0, y, z) for _, y, z in _ring(.43, size, "YZ", count=48)]
        return [xy, xz, yz]
    if shape == "IK Control":
        return [_square(size, plane),
                _scaled([(-.25, -.25), (.25, -.25), (.25, .25), (-.25, .25), (-.25, -.25)], size, plane),
                _ring(.10, size, plane, count=20)]
    if shape == "Slider":
        track = _scaled([(-.5, -.12), (.5, -.12), (.5, .12), (-.5, .12), (-.5, -.12)], size, plane)
        knob = _scaled([(-.10, -.25), (.10, -.25), (.10, .25), (-.10, .25), (-.10, -.25)], size, plane)
        ticks = [_scaled([(-.32, -.12), (-.32, .12)], size, plane),
                 _scaled([(.32, -.12), (.32, .12)], size, plane)]
        return [track, knob] + ticks
    if shape == "Stretch":
        shaft = _scaled([(0, -.34), (0, .34)], size, plane)
        bottom = _arrow_head((0, -.5), (0, -1), size, plane, .17, .12)
        top = _arrow_head((0, .5), (0, 1), size, plane, .17, .12)
        bars = [_scaled([(-.2, -.32), (.2, -.32)], size, plane),
                _scaled([(-.2, .32), (.2, .32)], size, plane)]
        return [shaft, bottom, top] + bars
    raise ValueError("Unknown controller shape: {}".format(shape))
