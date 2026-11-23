"""Maya 2027 shelf entry point for Curve Studio."""
import importlib

from curve_studio import geometry, tool

importlib.reload(geometry)
importlib.reload(tool)
StartUI = tool.StartUI


if __name__ == "__main__":
    StartUI()
