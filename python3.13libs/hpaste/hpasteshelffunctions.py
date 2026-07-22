import hou
import random
import string
crypto_available = True
try:
    from Crypto.Cipher import AES  # just for blocksize and constants
except Exception:  # not just import error, in case of buggy h19.5p3.9 it's syntax error
    crypto_available = False
    AES = None

try:
    from PySide6.QtWidgets import QApplication
    from PySide6 import QtCore as qtc
except ImportError:
    from PySide2.QtWidgets import QApplication
    from PySide2 import QtCore as qtc

from .hpaste import stringToNodes, nodesToString, InvalidContextError, WrongKeyLengthError, WrongKeyError, NoKeyError
from .QSnippetDetailsWidget import QSnippetDetailsWidget
from .hpasteweb import webPack, webUnpack

from . import hpasteoptions


def get_clipboard_text():
    if hou.applicationVersion()[0] > 15:
        return hou.ui.getTextFromClipboard()
    qapp = QApplication.instance()
    return qapp.clipboard().text()


def set_clipboard_text(s):
    if hou.applicationVersion()[0] > 15:
        hou.ui.copyTextToClipboard(s)
    else:
        qapp = QApplication.instance()
        qapp.clipboard().setText(s)


def show_waiting_cursor():
    if (20, 5) < hou.applicationVersion():
        # qt bug in 20.5.278 causes crash
        #  TODO: set upper version bound when fix released
        return
    qapp = QApplication.instance()
    if isinstance(qapp, QApplication):
        qapp.setOverrideCursor(qtc.Qt.WaitCursor)


def restore_cursor():
    if (20, 5) < hou.applicationVersion():
        # qt bug in 20.5.278 causes crash
        #  TODO: set upper version bound when fix released
        return
    qapp = QApplication.instance()
    if isinstance(qapp, QApplication):
        qapp.restoreOverrideCursor()


def hcopyweb():
    try:
        nodes = hou.selectedItems()
    except:
        nodes = hou.selectedNodes()

    if len(nodes) == 0:
        hou.ui.displayMessage("No nodes are selected!", severity=hou.severityType.Error)
        return

    enctype = hpasteoptions.getOption('hpasteweb.encryption_type', 'None')
    key = None
    encparms = {}
    if enctype == 'AES-CBC':
        if not crypto_available:
            hou.ui.displayMessage("PyCrypto seem to be broken in your version of houdini, cannot encrypt/decrypt")
            return
        key = ''.join([random.choice(string.ascii_letters + string.digits) for x in range(AES.block_size)])
        encparms = {'mode': AES.MODE_CBC}
        enctype = 'AES'
    elif enctype.lower() == 'none' or enctype == '':
        enctype = None

    if enctype is not None and key is None:
        print('Warning: unknown encryption method, disabling encryption')
        enctype = None

    try:
        s = nodesToString(nodes, encryption_type=enctype, key=key, **encparms)
    except RuntimeError as e:
        hou.ui.displayMessage("Error: %s" % str(e), severity=hou.severityType.Error)
        return

    show_waiting_cursor()
    try:
        s = webPack(s)
    except Exception as e:
        hou.ui.displayMessage(str(e), severity=hou.severityType.Error, title='error')
        return
    finally:
        restore_cursor()

    # append key to snippet
    if enctype is not None:
        s = key + '!' + s
    set_clipboard_text(s)
    hou.ui.setStatusMessage("Success: Cloud link copied to clipboard!")


def hpasteweb(pane=None):
    s = get_clipboard_text().strip()

    show_waiting_cursor()

    # check for compression key
    key = None
    if '!' in s:
        key, s = s.split('!', 1)
    try:
        s = webUnpack(s)
    except Exception as e:
        hou.ui.displayMessage(str(e), severity=hou.severityType.Error, title='error')
        return
    finally:
        restore_cursor()

    geonode = None
    for _ in range(2):
        try:
            stringToNodes(s, ne=pane, key=key, hou_parent=geonode)
        except InvalidContextError as e:
            nec, snc = e.contexts()
            if snc == 'Sop' and nec == 'Object':
                if hou.ui.displayMessage("Error: %s" % str(e), severity=hou.severityType.Warning, buttons=('Create geo node', 'Cancel'), default_choice=0, close_choice=1) == 0:
                    if geonode is not None:
                        raise RuntimeError('are we in an infinite loop?')
                    geonode = e.node().createNode('geo')
                    if pane is not None:
                        geonode.setPosition(pane.cursorPosition())
                    pane = None
                    continue
            else:
                hou.ui.displayMessage("Error: %s" % str(e), severity=hou.severityType.Error)
                return
        except WrongKeyLengthError as e:
            hou.ui.displayMessage("Bad key length: %s. Check if you copied hpaste link correctly" % str(e), severity=hou.severityType.Error)
            return
        except NoKeyError as e:
            hou.ui.displayMessage("This snippet is encrypted and requires a key: %s. Check if you copied hpaste link correctly. key in the link usually goes in front of the snippet, separated by '!'" % str(e), severity=hou.severityType.Error)
            return
        except WrongKeyError as e:
            hou.ui.displayMessage("Wrong key: %s. Check if you copied hpaste link correctly" % str(e), severity=hou.severityType.Error)
            return
        except RuntimeError as e:
            hou.ui.displayMessage("Error: %s" % str(e), severity=hou.severityType.Error)
            return
        except RuntimeWarning as e:
            hou.ui.displayMessage("Warning: %s" % str(e), severity=hou.severityType.Warning)
        break

    hou.ui.setStatusMessage("Success: Nodes pasted!")


def hpaste_inspect_tool(kwargs):
    try:
        parent = hou.qt.mainWindow()
    except:
        parent = hou.ui.mainQtWindow()

    w = QSnippetDetailsWidget(parent)
    surl = get_clipboard_text().strip()
    if '@' in surl:  # sanity check, just to not paste completely random things
        w.set_inspected_url(surl)

    w.show()
