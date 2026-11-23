"""Curve Studio UI and Maya scene operations for Maya 2027."""
from __future__ import annotations

import re
from pathlib import Path

from maya import OpenMayaUI, cmds
from PySide6 import QtCore, QtGui, QtWidgets
import shiboken6

from .geometry import ICON_FILES, PLANES, SHAPE_DESCRIPTIONS, SHAPE_NAMES, segments


AUTHOR = "shcgvfx"
ICON_DIR = Path(__file__).resolve().parent / "icons"
WINDOW_NAME = "CurveStudio2027"
COLORS = {
    "Default": None, "Red": 13, "Orange": 21, "Yellow": 17,
    "Green": 14, "Teal": 18, "Blue": 6, "Violet": 9,
    "Pink": 20, "White": 16,
}


def _main_window():
    pointer = OpenMayaUI.MQtUtil.mainWindow()
    return shiboken6.wrapInstance(int(pointer), QtWidgets.QWidget) if pointer else None


def _safe_name(text):
    result = re.sub(r"[^A-Za-z0-9_]+", "_", str(text).strip()).strip("_")
    if not result:
        result = "C_control_CTL"
    if result[0].isdigit():
        result = "C_" + result
    return result


def _curve_shapes(transform):
    return cmds.listRelatives(transform, shapes=True, noIntermediate=True,
                              fullPath=True, type="nurbsCurve") or []


def _selected_curve_transforms():
    found = []
    for node in cmds.ls(selection=True, long=True, objectsOnly=True) or []:
        if cmds.nodeType(node) == "nurbsCurve":
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            node = parents[0] if parents else node
        if cmds.nodeType(node) == "transform" and _curve_shapes(node) and node not in found:
            found.append(node)
    return found


def _create_control(shape, name, size, plane):
    outlines = segments(shape, size, plane)
    root = cmds.curve(name=_safe_name(name), degree=1, point=outlines[0])
    try:
        for outline in outlines[1:]:
            part = cmds.curve(name=_safe_name(name) + "_shape", degree=1, point=outline)
            part_shapes = _curve_shapes(part)
            if not part_shapes:
                raise RuntimeError("Maya did not create a curve shape for {}.".format(shape))
            cmds.parent(part_shapes, root, shape=True, relative=True)
            cmds.delete(part)
        if not _curve_shapes(root):
            raise RuntimeError("Maya did not create a curve shape for {}.".format(shape))
        return root
    except Exception:
        if cmds.objExists(root):
            cmds.delete(root)
        raise


def _local_curve_size(shapes):
    coords = []
    for shape in shapes:
        values = cmds.xform(shape + ".cv[*]", query=True, objectSpace=True, translation=True) or []
        coords.extend(values)
    if not coords:
        return 0.0
    spans = [max(coords[axis::3]) - min(coords[axis::3])
             for axis in range(3) if coords[axis::3]]
    return max(spans, default=0.0)


def _replace_shapes(targets, shape, size, plane, match_size=True):
    changed = []
    for target in targets:
        if not cmds.objExists(target):
            continue
        old_shapes = _curve_shapes(target)
        target_size = _local_curve_size(old_shapes) if match_size else 0.0
        requested_size = target_size if target_size > 1e-8 else size
        temp = _create_control(shape, "_curveStudioShape#", requested_size, plane)
        new_shapes = _curve_shapes(temp)
        if not new_shapes:
            cmds.delete(temp)
            raise RuntimeError("The replacement did not contain a curve shape.")
        try:
            cmds.parent(new_shapes, target, shape=True, relative=True)
            if old_shapes:
                cmds.delete(old_shapes)
            if cmds.objExists(temp):
                cmds.delete(temp)
            changed.append(target)
        except Exception:
            if cmds.objExists(temp):
                cmds.delete(temp)
            raise
    if not changed:
        raise RuntimeError("No selected curve controls could be changed.")
    return changed


def _apply_index_color(transforms, color_name, rgb=None):
    for transform in transforms:
        for shape in _curve_shapes(transform):
            if rgb is None and COLORS[color_name] is None:
                cmds.setAttr(shape + ".overrideRGBColors", False)
                cmds.setAttr(shape + ".overrideEnabled", False)
            else:
                cmds.setAttr(shape + ".overrideEnabled", True)
                if rgb is None:
                    cmds.setAttr(shape + ".overrideRGBColors", False)
                    cmds.setAttr(shape + ".overrideColor", COLORS[color_name])
                else:
                    cmds.setAttr(shape + ".overrideRGBColors", True)
                    cmds.setAttr(shape + ".overrideColorRGB", *rgb, type="double3")


class CurveStudioWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or _main_window())
        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle("Curve Studio | Maya 2027")
        self.setWindowFlags(QtCore.Qt.WindowType.Window
                            | QtCore.Qt.WindowType.WindowTitleHint
                            | QtCore.Qt.WindowType.WindowSystemMenuHint
                            | QtCore.Qt.WindowType.WindowMinMaxButtonsHint
                            | QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.setMinimumSize(390, 520)
        self.resize(440, 660)
        self.setSizeGripEnabled(True)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QDialog { background: #292b30; color: #e7e9ed; }
            QLabel { color: #c9ccd2; }
            QLineEdit, QComboBox, QListWidget, QDoubleSpinBox {
                background: #202226; color: #f2f3f5; border: 1px solid #42454c;
                border-radius: 4px; padding: 6px;
            }
            QPushButton { background: #3a3d44; color: #f3f4f6; border: 0;
                border-radius: 4px; padding: 8px; }
            QPushButton:hover { background: #4a4e57; }
            QPushButton#primary { background: #4b8bd8; font-weight: 600; }
            QGroupBox { border: 1px solid #42454c; border-radius: 5px;
                margin-top: 10px; padding: 8px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
        """)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(9)

        title = QtWidgets.QLabel("CURVE STUDIO")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: white;")
        layout.addWidget(title)
        layout.addWidget(QtWidgets.QLabel("Create a controller or replace the shape on selected controls."))

        self.shape_list = QtWidgets.QListWidget()
        self.shape_list.setIconSize(QtCore.QSize(36, 36))
        self.shape_list.setSpacing(2)
        for name in SHAPE_NAMES:
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, name)
            item.setToolTip(SHAPE_DESCRIPTIONS[name])
            icon = ICON_DIR / ICON_FILES[name]
            item.setIcon(QtGui.QIcon(str(icon)))
            self.shape_list.addItem(item)
        self.shape_list.setCurrentRow(0)
        self.shape_list.itemDoubleClicked.connect(self.create_control)
        layout.addWidget(self.shape_list, 1)

        options = QtWidgets.QGroupBox("Control options")
        form = QtWidgets.QFormLayout(options)
        self.name_field = QtWidgets.QLineEdit("C_control_CTL")
        self.size_field = QtWidgets.QDoubleSpinBox()
        self.size_field.setRange(0.01, 10000.0)
        self.size_field.setDecimals(2)
        self.size_field.setValue(2.0)
        self.size_field.setSuffix(" units")
        self.plane_field = QtWidgets.QComboBox()
        self.plane_field.addItems(PLANES)
        self.match_size = QtWidgets.QCheckBox("Match existing shape size on replace")
        self.match_size.setChecked(True)
        form.addRow("Name", self.name_field)
        form.addRow("Size", self.size_field)
        form.addRow("Plane", self.plane_field)
        form.addRow("Replace", self.match_size)
        layout.addWidget(options)

        create = QtWidgets.QPushButton("Create control")
        create.setObjectName("primary")
        create.clicked.connect(self.create_control)
        layout.addWidget(create)
        replace = QtWidgets.QPushButton("Replace selected shape")
        replace.clicked.connect(self.replace_selected)
        layout.addWidget(replace)

        color_row = QtWidgets.QHBoxLayout()
        self.color_field = QtWidgets.QComboBox()
        self.color_field.addItems(COLORS.keys())
        color_row.addWidget(self.color_field, 1)
        color_button = QtWidgets.QPushButton("Apply color")
        color_button.clicked.connect(self.apply_color)
        color_row.addWidget(color_button)
        custom = QtWidgets.QPushButton("Custom...")
        custom.clicked.connect(self.apply_custom_color)
        color_row.addWidget(custom)
        layout.addLayout(color_row)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #aeb3bd; padding: 3px;")
        layout.addWidget(self.status)
        grip_row = QtWidgets.QHBoxLayout()
        grip_row.addStretch(1)
        grip = QtWidgets.QSizeGrip(self)
        grip.setToolTip("Drag to resize")
        grip_row.addWidget(grip)
        layout.addLayout(grip_row)

    def _selected_shape(self):
        item = self.shape_list.currentItem()
        if item is None:
            raise ValueError("Choose a controller shape.")
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    def _run(self, description, operation):
        cmds.undoInfo(openChunk=True, chunkName="CurveStudio_" + description.replace(" ", "_"))
        failed = False
        try:
            result = operation()
            self.status.setText(description)
            return result
        except Exception as exc:
            failed = True
            self.status.setText("Could not {}: {}".format(description.lower(), exc))
            cmds.warning("Curve Studio: {}".format(exc))
            return None
        finally:
            cmds.undoInfo(closeChunk=True)
            if failed:
                try:
                    if str(cmds.undoInfo(query=True, undoName=True)).startswith("CurveStudio_"):
                        cmds.undo()
                except Exception:
                    pass

    def create_control(self, *_):
        def action():
            node = _create_control(self._selected_shape(), self.name_field.text(),
                                   self.size_field.value(), self.plane_field.currentText())
            cmds.select(node, replace=True)
            return node
        return self._run("Created control", action)

    def replace_selected(self, *_):
        targets = _selected_curve_transforms()
        if not targets:
            self.status.setText("Select one or more curve controls first.")
            return None
        return self._run("Replaced {} shape(s)".format(len(targets)), lambda: _replace_shapes(
            targets, self._selected_shape(), self.size_field.value(),
            self.plane_field.currentText(), self.match_size.isChecked()))

    def apply_color(self, *_):
        targets = _selected_curve_transforms()
        if not targets:
            self.status.setText("Select one or more curve controls first.")
            return None
        color = self.color_field.currentText()
        return self._run("Applied {} color".format(color),
                         lambda: _apply_index_color(targets, color))

    def apply_custom_color(self, *_):
        targets = _selected_curve_transforms()
        if not targets:
            self.status.setText("Select one or more curve controls first.")
            return None
        color = QtWidgets.QColorDialog.getColor(parent=self)
        if not color.isValid():
            return None
        rgb = (color.redF(), color.greenF(), color.blueF())
        return self._run("Applied custom color", lambda: _apply_index_color(targets, "Default", rgb))

    def closeEvent(self, event):
        event.accept()


_window = None


def StartUI():
    global _window
    if _window is not None and shiboken6.isValid(_window):
        _window.close()
        _window.deleteLater()
    _window = CurveStudioWindow(_main_window())
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window
