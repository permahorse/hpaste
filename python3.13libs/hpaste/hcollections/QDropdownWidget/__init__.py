_qt = 5
try:
    import PySide6
    _qt = 6
except ImportError:
    pass

if _qt == 6:
    from .qt6 import *
elif _qt == 5:
    from .qt5 import *
else:
    raise NotImplementedError()
