"""Install or refresh the Curve Studio button on Maya's Custom shelf."""
from pathlib import Path
import shutil
import time

from maya import cmds, mel


def install():
    shelf_top = mel.eval("$tmp = $gShelfTopLevel")
    shelves = cmds.shelfTabLayout(shelf_top, query=True, childArray=True) or []
    shelf = next((item for item in shelves if item.rsplit("|", 1)[-1] == "Custom"), None)
    if shelf is None:
        shelf = cmds.shelfLayout("Custom", parent=shelf_top)
    tag = "curveStudio/2027/launch"
    children = cmds.shelfLayout(shelf, query=True, childArray=True) or []
    button = next((item for item in children
                   if cmds.objectTypeUI(item) == "shelfButton"
                   and (cmds.shelfButton(item, query=True, docTag=True) == tag
                        or cmds.shelfButton(item, query=True, label=True) == "Curve Recreator")), None)
    script_dir = Path(__file__).resolve().parent
    icon = script_dir / "curve_studio" / "icons" / "circle.svg"
    command = "import importlib\nimport curveStudio\nimportlib.reload(curveStudio)\ncurveStudio.StartUI()"
    options = dict(label="Curve Studio", annotation="Open Curve Studio for Maya 2027",
                   image=str(icon) if icon.is_file() else "commandButton.png",
                   sourceType="python", command=command, docTag=tag, width=36, height=36)
    if button:
        cmds.shelfButton(button, edit=True, **options)
    else:
        button = cmds.shelfButton(parent=shelf, **options)
    destination = Path(cmds.internalVar(userShelfDir=True)) / "shelf_Custom.mel"
    if destination.exists():
        backup = Path(str(destination) + ".backup-" + time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(str(destination), str(backup))
    if not cmds.saveShelf(shelf, str(destination.with_suffix(""))):
        raise RuntimeError("Could not save the Custom shelf")
    cmds.shelfTabLayout(shelf_top, edit=True, selectTab=shelf)
    return button


if __name__ == "__main__":
    install()
