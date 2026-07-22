# this will have a list of available plugins
import os
import importlib
import inspect
from ..webclipboardbase import WebClipBoardBase

pluginClassList = []
pluginModuleList = []


def rescanPlugins():
    global pluginClassList
    global pluginModuleList
    global __all__
    pluginClassList = []
    pluginModuleList = []
    files = [os.path.splitext(x)[0] for x in os.listdir(os.path.dirname(__file__)) if os.path.splitext(x)[1] == ".py" and x != "__init__.py"]
    __all__ = files
    for fn in files:
        try:
            newmodule = importlib.import_module(".".join((__name__, fn)))
            importlib.reload(newmodule)
        except Exception as e:
            print("hpaste web plugins: failed to load module {} because of: {}".format(fn, str(e)))
            continue
        pluginModuleList.append(newmodule)
        for name, obj in inspect.getmembers(newmodule):
            if inspect.isclass(obj) and WebClipBoardBase in inspect.getmro(obj)[1:]:
                pluginClassList.append(obj)


rescanPlugins()
