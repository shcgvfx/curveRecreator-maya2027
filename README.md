# Curve Studio | Maya 2027

Curve Studio is an original, self-contained controller-shape utility for
Autodesk Maya 2027. The source contains no imported controller presets or
third-party curve library.

Author: **shcgvfx**

## Features

- Create Circle, Square, Triangle, Box, Arrow, Cross, and Locator controls.
- Set control name, size, and the plane for planar shapes.
- Replace curve shapes on one or more selected controls while preserving their
  transform nodes, hierarchy, and custom attributes.
- Match the old shape's local size during replacement or use the size field.
- Apply Maya indexed colors or a custom RGB color.
- Resize the window by dragging its borders or the lower-right grip.
- Undo each scene action as one Maya undo step.

There is no preset browser, custom preset folder, or legacy curve library.

## Install

Copy `curveStudio.py`, `install_curve_studio_shelf.py`, and the
`curve_studio` folder into Maya 2027's user `scripts` directory. Run
`install_curve_studio_shelf.py` from Maya's Python Script Editor once to add or
refresh the Custom shelf button. To open directly:

```python
import importlib
import curveStudio
importlib.reload(curveStudio)
curveStudio.StartUI()
```

## Unit tests

Run `python -m unittest discover -s tests -v`. Scene operations use a Maya
command mock; the geometry, all shape variants, shape replacement, transform
preservation, color assignment, icon coverage, and resize affordance are tested.
