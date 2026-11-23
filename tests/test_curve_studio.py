"""Unit tests for Curve Studio's geometry and Maya command operations."""
import ast
import importlib.util
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from curve_studio.geometry import (
    ICON_FILES, PLANES, SHAPE_DESCRIPTIONS, SHAPE_NAMES, segments,
)


class FakeMayaCmds:
    def __init__(self):
        self.transforms = {}
        self.shapes = {}
        self.selection = []
        self.attrs = {}
        self.undo_count = 0

    def _find(self, node):
        node = str(node).split(".", 1)[0]
        if node in self.transforms or node in self.shapes:
            return node
        short = node.rsplit("|", 1)[-1]
        for path, data in self.transforms.items():
            if data["name"] == short:
                return path
        for path in self.shapes:
            if path.rsplit("|", 1)[-1] == short:
                return path
        return None

    def curve(self, name="curve", degree=1, point=None, **kwargs):
        name = str(name).replace("#", "1")
        base, number = name, 1
        while any(item["name"] == name for item in self.transforms.values()):
            number += 1
            name = base + str(number)
        transform = "|" + name
        shape = transform + "|" + name + "Shape"
        points = list(point or [])
        self.transforms[transform] = {"name": name, "shapes": [shape], "custom": 27}
        self.shapes[shape] = {"owner": transform, "points": points}
        return name

    def listRelatives(self, node, **kwargs):
        path = self._find(node)
        if not path:
            return []
        if kwargs.get("parent"):
            parent = self.shapes.get(path, {}).get("owner")
            return [parent] if parent else []
        if path in self.transforms:
            return list(self.transforms[path]["shapes"])
        return []

    def nodeType(self, node):
        return "nurbsCurve" if self._find(node) in self.shapes else "transform"

    def ls(self, **kwargs):
        if kwargs.get("selection"):
            return list(self.selection)
        node_type = kwargs.get("type")
        if node_type == "transform":
            values = list(self.transforms)
        elif node_type == "nurbsCurve":
            values = list(self.shapes)
        else:
            values = list(self.transforms) + list(self.shapes)
        if kwargs.get("long"):
            return values
        return [value.rsplit("|", 1)[-1] for value in values]

    def parent(self, children, parent, **kwargs):
        parent_path = self._find(parent)
        if not isinstance(children, (list, tuple)):
            children = [children]
        for child in children:
            child_path = self._find(child)
            if child_path not in self.shapes or parent_path not in self.transforms:
                continue
            data = self.shapes.pop(child_path)
            old_parent = data["owner"]
            self.transforms[old_parent]["shapes"].remove(child_path)
            new_path = parent_path + "|" + child_path.rsplit("|", 1)[-1]
            data["owner"] = parent_path
            self.shapes[new_path] = data
            self.transforms[parent_path]["shapes"].append(new_path)
        return children

    def delete(self, nodes):
        if not isinstance(nodes, (list, tuple)):
            nodes = [nodes]
        for node in nodes:
            path = self._find(node)
            if path in self.transforms:
                for shape in self.transforms[path]["shapes"]:
                    self.shapes.pop(shape, None)
                self.transforms.pop(path, None)
            elif path in self.shapes:
                owner = self.shapes[path]["owner"]
                self.transforms[owner]["shapes"].remove(path)
                self.shapes.pop(path, None)

    def xform(self, component, **kwargs):
        path = self._find(component)
        points = self.shapes[path]["points"]
        return [coordinate for point in points for coordinate in point]

    def objExists(self, node):
        path = self._find(node)
        return path in self.transforms or path in self.shapes

    def select(self, nodes, **kwargs):
        self.selection = list(nodes) if isinstance(nodes, (list, tuple)) else [nodes]

    def setAttr(self, plug, *values, **kwargs):
        self.attrs[plug] = values[0] if len(values) == 1 else values

    def undoInfo(self, **kwargs):
        return "CurveStudio_Test" if kwargs.get("query") else None

    def undo(self):
        self.undo_count += 1

    def warning(self, message):
        return None


def load_tool(fake):
    maya = ModuleType("maya")
    maya.__path__ = []
    maya_cmds = ModuleType("maya.cmds")
    maya_cmds.__getattr__ = lambda name: getattr(fake, name)
    maya.cmds = maya_cmds
    maya.OpenMayaUI = SimpleNamespace(MQtUtil=SimpleNamespace(mainWindow=lambda: 0))

    qt_core = ModuleType("PySide6.QtCore")
    qt_core.Qt = SimpleNamespace()
    qt_gui = ModuleType("PySide6.QtGui")
    qt_widgets = ModuleType("PySide6.QtWidgets")
    qt_widgets.QDialog = type("QDialog", (), {})
    qt = ModuleType("PySide6")
    qt.QtCore, qt.QtGui, qt.QtWidgets = qt_core, qt_gui, qt_widgets
    shiboken = ModuleType("shiboken6")
    shiboken.wrapInstance = lambda *_: None
    shiboken.isValid = lambda *_: True
    with mock.patch.dict(sys.modules, {
        "maya": maya, "maya.cmds": maya_cmds, "PySide6": qt,
        "PySide6.QtCore": qt_core, "PySide6.QtGui": qt_gui,
        "PySide6.QtWidgets": qt_widgets, "shiboken6": shiboken,
    }):
        name = "curve_studio.tool_under_test"
        spec = importlib.util.spec_from_file_location(name, ROOT / "curve_studio" / "tool.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


class GeometryTests(unittest.TestCase):
    def test_every_shape_has_geometry_in_every_plane(self):
        for name in SHAPE_NAMES:
            for plane in PLANES:
                with self.subTest(shape=name, plane=plane):
                    result = segments(name, 2.0, plane)
                    self.assertTrue(result)
                    self.assertTrue(all(len(point) == 3 for line in result for point in line))

    def test_size_scales_outline_linearly(self):
        small = segments("Square", 1.0, "XY")
        large = segments("Square", 4.0, "XY")
        self.assertEqual(large[0][0], tuple(value * 4 for value in small[0][0]))

    def test_planar_shapes_respect_plane_mapping(self):
        self.assertTrue(all(abs(p[2]) < 1e-8 for line in segments("Triangle", 2, "XY") for p in line))
        self.assertTrue(all(abs(p[1]) < 1e-8 for line in segments("Arrow", 2, "XZ") for p in line))
        self.assertTrue(all(abs(p[0]) < 1e-8 for line in segments("Locator", 2, "YZ") for p in line))

    def test_pole_vector_shape_has_kite_outline_and_center_marker(self):
        result = segments("Pole Vector", 2.0, "XZ")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0][0], result[0][-1])
        self.assertEqual(result[1][0][0], 0.0)
        self.assertTrue(any(len(line) > 10 for line in result))

    def test_roll_shape_has_a_sweeping_arc_and_arrow_head(self):
        result = segments("Roll", 2.0, "XY")
        self.assertEqual(len(result), 2)
        self.assertGreater(len(result[0]), 40)
        self.assertEqual(result[1][0], result[1][-1])

    def test_reverse_roll_points_and_arrow_in_opposite_direction(self):
        forward = segments("Roll", 2.0, "XY")
        reverse = segments("Roll Reverse", 2.0, "XY")
        self.assertAlmostEqual(forward[0][0][0], reverse[0][-1][0], places=7)
        self.assertAlmostEqual(forward[0][0][1], reverse[0][-1][1], places=7)
        self.assertEqual(len(reverse), 2)
        self.assertEqual(reverse[1][0], reverse[1][-1])

    def test_spiral_shapes_turn_in_opposite_directions_on_every_plane(self):
        for plane in PLANES:
            with self.subTest(plane=plane):
                clockwise = segments("Spiral CW", 2.0, plane)
                counterclockwise = segments("Spiral CCW", 2.0, plane)
                self.assertEqual(len(clockwise[0]), 101)
                self.assertEqual(len(counterclockwise[0]), 101)
                self.assertEqual(clockwise[1][0], clockwise[1][-1])
                self.assertEqual(counterclockwise[1][0], counterclockwise[1][-1])
                self.assertNotEqual(clockwise[0][10], counterclockwise[0][10])
                zero_axis = {"XY": 2, "XZ": 1, "YZ": 0}[plane]
                self.assertTrue(all(abs(point[zero_axis]) < 1e-9
                                    for line in clockwise + counterclockwise for point in line))

    def test_bidirectional_arrow_is_a_closed_two_headed_outline(self):
        for plane in PLANES:
            with self.subTest(plane=plane):
                result = segments("Bidirectional Arrow", 2.0, plane)
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0][0], result[0][-1])
                axis = {"XY": 2, "XZ": 1, "YZ": 0}[plane]
                self.assertTrue(all(abs(point[axis]) < 1e-9 for point in result[0]))
                outline_axis = {"XY": 0, "XZ": 0, "YZ": 1}[plane]
                self.assertAlmostEqual(min(point[outline_axis] for point in result[0]), -1.0)
                self.assertAlmostEqual(max(point[outline_axis] for point in result[0]), 1.0)

    def test_lollipop_finger_stem_is_anchored_at_origin(self):
        for plane in PLANES:
            with self.subTest(plane=plane):
                stem, head = segments("Lollipop Finger", 2.0, plane)
                self.assertEqual(stem[0], (0.0, 0.0, 0.0))
                expected_tip = {"XY": (0.0, .92, 0.0),
                                "XZ": (0.0, 0.0, .92),
                                "YZ": (0.0, 0.0, .92)}[plane]
                self.assertEqual(stem[1], expected_tip)
                self.assertTrue(all(abs(a - b) < 1e-8 for a, b in zip(head[0], head[-1])))

    def test_foot_global_fk_ik_slider_and_stretch_are_distinct_shapes(self):
        shapes = ("Foot", "Global", "FK Control", "IK Control", "Slider", "Stretch")
        outlines = {name: segments(name, 2.0, "XY") for name in shapes}
        self.assertEqual(len({tuple(map(len, lines)) for lines in outlines.values()}), len(shapes))

    def test_invalid_size_plane_and_shape_are_rejected(self):
        for size in (0, -1, float("inf"), "bad"):
            with self.subTest(size=size), self.assertRaises(ValueError):
                segments("Circle", size)
        with self.assertRaises(ValueError):
            segments("Circle", 2, "bad")
        with self.assertRaises(ValueError):
            segments("Octagon", 2)


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.cmds = FakeMayaCmds()
        self.tool = load_tool(self.cmds)

    def test_create_every_shape_builds_expected_curve_nodes(self):
        for name in SHAPE_NAMES:
            with self.subTest(shape=name):
                fresh = FakeMayaCmds()
                tool = load_tool(fresh)
                node = tool._create_control(name, "C_test_CTL", 2.0, "XY")
                transform = fresh._find(node)
                self.assertEqual(len(fresh.transforms[transform]["shapes"]),
                                 len(segments(name, 2.0, "XY")))

    def test_replacement_keeps_transform_and_custom_attributes(self):
        target = self.cmds.curve(name="existing", point=[(-1, 0, 0), (1, 0, 0)])
        target_path = self.cmds._find(target)
        transform_data = self.cmds.transforms[target_path]
        old_shapes = list(transform_data["shapes"])
        result = self.tool._replace_shapes([target_path], "Square", 5, "XY")
        self.assertEqual(result, [target_path])
        self.assertIs(self.cmds.transforms[target_path], transform_data)
        self.assertEqual(transform_data["custom"], 27)
        self.assertTrue(all(shape not in self.cmds.shapes for shape in old_shapes))
        self.assertEqual(len(transform_data["shapes"]), 1)

    def test_replacement_respects_manual_size_option(self):
        target = self.cmds.curve(name="existing", point=[(-1, 0, 0), (1, 0, 0)])
        target_path = self.cmds._find(target)
        self.tool._replace_shapes([target_path], "Triangle", 3.0, "XY", match_size=False)
        shape = self.cmds.transforms[target_path]["shapes"][0]
        xs = [p[0] for p in self.cmds.shapes[shape]["points"]]
        self.assertAlmostEqual(max(xs) - min(xs), 3.0)

    def test_selection_filter_ignores_non_curve_transforms(self):
        node = self.cmds.curve(name="selected", point=[(0, 0, 0), (1, 0, 0)])
        self.cmds.selection = [self.cmds._find(node)]
        self.assertEqual(self.tool._selected_curve_transforms(), [self.cmds._find(node)])

    def test_color_assignment_supports_indexed_rgb_and_reset(self):
        node = self.cmds.curve(name="colored", point=[(0, 0, 0), (1, 0, 0)])
        transform = self.cmds._find(node)
        shape = self.cmds.transforms[transform]["shapes"][0]
        self.tool._apply_index_color([transform], "Blue")
        self.assertEqual(self.cmds.attrs[shape + ".overrideColor"], 6)
        self.tool._apply_index_color([transform], "Default")
        self.assertFalse(self.cmds.attrs[shape + ".overrideEnabled"])
        self.tool._apply_index_color([transform], "Default", (0.1, 0.2, 0.3))
        self.assertTrue(self.cmds.attrs[shape + ".overrideRGBColors"])

    def test_action_failure_rolls_back_its_undo_chunk(self):
        window = self.tool.CurveStudioWindow.__new__(self.tool.CurveStudioWindow)
        window.status = SimpleNamespace(setText=lambda *_: None)
        result = window._run("Test failure", lambda: (_ for _ in ()).throw(RuntimeError("failed")))
        self.assertIsNone(result)
        self.assertEqual(self.cmds.undo_count, 1)


class PackageTests(unittest.TestCase):
    def test_every_shape_has_a_valid_svg_icon(self):
        for name in SHAPE_NAMES:
            with self.subTest(shape=name):
                icon = ROOT / "curve_studio" / "icons" / ICON_FILES[name]
                ET.parse(icon)
                self.assertTrue(SHAPE_DESCRIPTIONS[name])
        self.assertEqual(set(ICON_FILES), set(SHAPE_NAMES))
        self.assertEqual(set(SHAPE_DESCRIPTIONS), set(SHAPE_NAMES))

    def test_roll_icons_match_single_arc_and_single_direction_geometry(self):
        for name in ("Roll", "Roll Reverse"):
            with self.subTest(shape=name):
                root = ET.parse(ROOT / "curve_studio" / "icons" / ICON_FILES[name]).getroot()
                paths = root.findall(".//{http://www.w3.org/2000/svg}path")
                self.assertEqual(len(paths), 2)
                self.assertIn("A", paths[0].get("d", ""))
                self.assertFalse(root.findall(".//{http://www.w3.org/2000/svg}circle"))

    def test_resizing_controls_are_present(self):
        tree = ast.parse((ROOT / "curve_studio" / "tool.py").read_text(encoding="utf-8"))
        calls = {node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertTrue({"resize", "setSizeGripEnabled"}.issubset(calls))
        self.assertIn("QSizeGrip", {node.attr for node in ast.walk(tree)
                                    if isinstance(node, ast.Attribute)})

    def test_distribution_has_no_legacy_library_or_preset_folder(self):
        self.assertFalse((ROOT / "Curves").exists())
        self.assertFalse((ROOT / "curve_studio" / "Curves").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
