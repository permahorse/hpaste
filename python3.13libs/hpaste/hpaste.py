import os

try:
    import hou
except ImportError:
    import sys
    print('hou not found! proceeding with limited functionality', file=sys.stderr)

import json
import re
import hashlib
import binascii
import base64
import bz2

crypto_available = True
try:
    from Crypto.Cipher import AES
    from Crypto import Random as CRandom
except Exception:  # not just import error, in case of buggy h19.5p3.9 it's syntax error
    crypto_available = False
    AES = Random = CRandom = None

import struct

import tempfile

opt = None
try:
    from . import hpasteoptions as opt
except:
    print("Hpaste: Failed to load options, using defaults")

try:
    from .hipmetastrip import clean_meta
except ImportError:
    def clean_meta(x):  # type: (bytes) -> bytes
        return x


try:
    from typing import Callable, Tuple, Optional
except ImportError:
    pass

current_format_version = (2, 2)


class InvalidContextError(RuntimeError):
    def __init__(self, parent_node, snippetcontext):
        super(InvalidContextError, self).__init__("this snippet has '%s' context" % snippetcontext)
        self.__necontext = getChildContext(parent_node, hou.applicationVersion())
        self.__snippetcontext = snippetcontext
        self.__node = parent_node

    def contexts(self):
        return self.__necontext, self.__snippetcontext

    def node(self):
        return self.__node


class WrongKeyError(RuntimeError):
    pass


class WrongKeyLengthError(WrongKeyError):
    pass


class NoKeyError(WrongKeyError):
    pass


def orderSelected():
    return orderNodes(hou.selectedNodes())


def orderNodes(nodes):
    """
    take a list of nodes, return a specially sorted list of nodes in order to proprely recreate them later
    """
    if len(nodes) == 0:
        return []

    parent = nodes[0].parent()
    for node in nodes:
        if node.parent() != parent: raise RuntimeError("selected nodes must have the same parent!")

    snodes = [x for x in nodes if len([y for y in x.inputs() if y in nodes]) == 0]  # init with leaf nodes

    for node in snodes:
        for output in (x for x in node.outputs() if x in nodes):
            if output in snodes:
                snodes.remove(output)  # TODO: uff.... maybe there's a more optimized way?
            snodes.append(output)

    return snodes


def getChildContext(node, houver):
    if houver[0] >= 16:
        return node.type().childTypeCategory().name()
    elif houver[0] <= 15 and houver >= 10:
        return node.childTypeCategory().name()
    else:
        raise RuntimeError("unsupported houdini version!")


def getSerializer(enctype: Optional[str] = None, **kwargs) -> Tuple[Optional[dict], Callable[[bytes], bytes]]:  # TODO: makes more sense for serializer to return str
    if enctype == 'AES':
        if not crypto_available:
            raise RuntimeError('PyCrypto is not available, cannot encrypt/decrypt')
        rng = CRandom.new()
        key = kwargs['key'].encode('UTF-8')
        mode = kwargs.get('mode', AES.MODE_CBC)
        iv = kwargs.get('iv', rng.read(AES.block_size))
        magic_footer = (b'--===E)*(3===--.' * (AES.block_size // 16 + int(AES.block_size % 16 > 0)))[:AES.block_size]

        def _ser(x: bytes):
            enc = AES.new(key, mode, iv)
            xsize = len(x)
            xbytes = b''.join((struct.pack('>Q', xsize), x))
            rng = CRandom.new()
            pad = rng.read(AES.block_size - len(xbytes) % AES.block_size)
            return base64.b64encode(enc.encrypt(b''.join((xbytes, pad, magic_footer))))

        return {'iv': base64.b64encode(iv).decode('UTF-8'), 'mode': mode}, _ser
    elif enctype is None or enctype.lower() == 'none':
        return None, lambda x: base64.b64encode(x)
    else:
        raise RuntimeError('Encryption type unsupported. try updating hpaste')


def getDeserializer(enctype: Optional[str] = None, **kwargs) -> Callable[[bytes], bytes]:
    if enctype == 'AES':
        if not crypto_available:
            raise RuntimeError('PyCrypto is not available, cannot encrypt/decrypt')
        key = kwargs['key'].encode('UTF-8')
        if key is None:
            raise NoKeyError('no decryption key provided for encryption type AES')
        mode = kwargs['mode']
        iv = base64.b64decode(kwargs['iv'].encode('UTF-8'))
        magic_footer = (b'--===E)*(3===--.' * (AES.block_size // 16 + int(AES.block_size % 16 > 0)))[:AES.block_size]

        def _deser(x):
            try:
                enc = AES.new(key, mode, iv)
            except ValueError as e:
                if str(e).startswith('AES key must'):
                    raise WrongKeyLengthError('invalid key length!')
                raise
            xbytes = enc.decrypt(base64.b64decode(x))
            xsize = struct.unpack('>Q', xbytes[:8])[0]
            if xsize < 0 or xsize > len(xbytes) or len(xbytes) - xsize - 8 > 2 * AES.block_size or xbytes[-AES.block_size:] != magic_footer:
                raise WrongKeyError('seems that provided decryption key is wrong')
            return xbytes[8: 8 + xsize]

        return _deser
    elif enctype is None or enctype == '' or enctype.lower() == 'none':
        return lambda x: base64.b64decode(x)
    else:
        raise RuntimeError('Encryption type unsupported. try updating hpaste')


def nodesToString(nodes, transfer_assets=None, encryption_type=None, clean_metadata=None, **kwargs) -> str:
    """
        nodes : hou.NetworkMovableItems
    algtype:
        0 - python code based algorythm
        1 - new h16 serialization, much prefered!
    :param nodes:
    :param transfer_assets:
    :param encryption_type: type of encryption to use
    :param clean_metadata: whether to clean code from metadata or no. this does not
    :return:
    """

    enc_data, serialize = getSerializer(encryption_type, **kwargs)

    if transfer_assets is None:
        transfer_assets = True
        if opt is not None:
            transfer_assets = opt.getOption('hpaste.transfer_assets', transfer_assets)

    parent = nodes[0].parent()
    for node in nodes:
        if node.parent() != parent:
            raise RuntimeError("selected items must have the same parent!")

    algtype = 1
    houver = hou.applicationVersion()
    if houver[0] < 10:
        raise RuntimeError("sorry, unsupported for now")
    elif houver[0] <= 15 and houver[0] >= 10:
        algtype = 1
    elif houver[0] >= 16:
        algtype = 2

    # print("using algorithm %d"%algtype)
    if algtype == 0:
        nodes = orderNodes(nodes)

    context = getChildContext(parent, houver)

    code = ''
    hdaList = []
    if algtype == 0:
        # filter to keep only nodes
        nodes = [x for x in nodes if isinstance(x, hou.Node)]
        for node in nodes:
            newcode = node.asCode(recurse=True)
            if len(node.inputs()) > 0:
                # there's a bug(from our pov) of name clashing for default connection code for top node
                newcode = re.sub(r'# Code to establish connections for.+\n.+\n', '# filtered lines\n', newcode, 1)
            code += newcode
    elif algtype == 1 or algtype == 2:
        if transfer_assets:  # added in version 2.1
            # scan for nonstandard asset definitions
            hfs = os.environ['HFS']
            already_stashed = set()
            for elem in nodes:
                if not isinstance(elem, hou.Node):
                    continue
                for node in [elem] + list(elem.allSubChildren()):
                    if not isinstance(node, hou.Node):
                        continue
                    if node.type().nameComponents() in already_stashed:
                        continue
                    already_stashed.add(node.type().nameComponents())
                    definition = node.type().definition()
                    if definition is None:
                        continue
                    libpath = definition.libraryFilePath()
                    if libpath.startswith(hfs):
                        continue
                    # at this point we've got a non standard asset definition
                    # print(libpath)
                    fd, temppath = tempfile.mkstemp()
                    try:
                        definition.copyToHDAFile(temppath)
                        with open(temppath, 'rb') as f:
                            hdacode = f.read()
                        hdaList.append({'type': node.type().name(), 'category': node.type().category().name(), 'code': serialize(hdacode).decode('UTF-8')})
                    finally:
                        os.close(fd)

        # get temp file
        fd, temppath = tempfile.mkstemp()
        try:
            if algtype == 1:
                # filter to keep only nodes
                nodes = [x for x in nodes if isinstance(x, hou.Node)]
                nodes[0].parent().saveChildrenToFile(nodes, (), temppath)
            if algtype == 2:
                nodes[0].parent().saveItemsToFile(nodes, temppath, False)  # true or false....
            with open(temppath, "rb") as f:
                code = f.read()
        finally:
            os.close(fd)

        if clean_metadata or clean_metadata is None and opt is not None and opt.getOption('hpaste.strip_metadata', False):
            code = clean_meta(code)
    code = serialize(code)

    data = dict()
    data['algtype'] = algtype
    data['version'] = current_format_version[0]
    data['version.minor'] = current_format_version[1]
    data['houver'] = houver
    data['context'] = context
    data['code'] = code.decode('UTF-8')  # utf8 here doesnt matter since we work within base64
    data['hdaList'] = hdaList
    data['chsum'] = hashlib.sha1(code).hexdigest()
    # security entries, for future
    data['author'] = 'unknown'
    data['encrypted'] = encryption_type is not None
    data['encryptionType'] = encryption_type
    data['encryptionData'] = enc_data
    data['signed'] = False
    data['signatureType'] = ''
    data['signatureData'] = None
    # these suppose there is a trusted vendors list with their public keys stored

    stringdata = base64.urlsafe_b64encode(bz2.compress(json.dumps(data).encode('UTF-8')))

    return stringdata.decode('UTF-8')


def stringToData(s: str, key=None) -> (dict, Optional[Callable[[bytes], bytes]]):  # TODO: use this in stringToNodes
    s = s.encode('UTF-8')  # ununicode. there should not be any unicode in it anyways
    try:
        data = json.loads(bz2.decompress(base64.urlsafe_b64decode(s)).decode('UTF-8'))
    except Exception as e:
        raise RuntimeError("input data is either corrupted or just not a nodecode: " + repr(e))

    # check version
    formatVersion = data['version']
    if formatVersion > current_format_version[0]:
        raise RuntimeError("unsupported version of data format. Try updating hpaste to the latest version")
    if data.get('version.minor', 0) > current_format_version[1]:
        print('HPaste: Warning!! snippet has later format version than hpaste. Consider updating hpaste to the latest version')
    if data.get('signed', False):
        print('HPaste: Warning!! this snippet seem to be signed, but this version of HPaste has no idea how to check signatures! so signature check will be skipped!')

    try:
        deserializer = getDeserializer(enctype=data.get('encryptionType', None), key=key, **(data.get('encryptionData', None) or {}))
    except NoKeyError:
        deserializer = None

    return data, deserializer


def stringToNodes(s: str, hou_parent=None, ne=None, ignore_hdas_if_already_defined=None, force_prefer_hdas=None, override_network_position=None, key=None):
    """
    TODO: here to be a docstring
    :param s:
    :param hou_parent:
    :param ne:
    :param ignore_hdas_if_already_defined:
    :param force_prefer_hdas:
    :override_network_position: hou.Vector2 - position in networkview pane
    :return:
    """
    if ignore_hdas_if_already_defined is None:
        ignore_hdas_if_already_defined = True
        if opt is not None:
            ignore_hdas_if_already_defined = opt.getOption('hpaste.ignore_hdas_if_already_defined', ignore_hdas_if_already_defined)

    if force_prefer_hdas is None:
        force_prefer_hdas = False
        if opt is not None:
            force_prefer_hdas = opt.getOption('hpaste.force_prefer_hdas', force_prefer_hdas)

    s = s.encode('UTF-8')  # ununicode. there should not be any unicode in it anyways
    try:
        data = json.loads(bz2.decompress(base64.urlsafe_b64decode(s)).decode('UTF-8'))
    except Exception as e:
        raise RuntimeError("input data is either corrupted or just not a nodecode: " + repr(e))

    houver1 = hou.applicationVersion()

    paste_to_position = ne is not None or override_network_position is not None
    if hou_parent is None:
        if ne is None:
            nes = [x for x in hou.ui.paneTabs() if x.type() == hou.paneTabType.NetworkEditor and getChildContext(x.pwd(), houver1) == data['context']]
            if len(nes) == 0:
                nes = [x for x in hou.ui.paneTabs() if x.type() == hou.paneTabType.NetworkEditor]
                if len(nes) == 0:
                    raise RuntimeError("this snippet has '{0}' context. cannot find opened network editor with context '{0}' to paste in".format(data['context']))
            ne = nes[0]
        hou_parent = ne.pwd()

    # check version
    formatVersion = data['version']
    if formatVersion > current_format_version[0]:
        raise RuntimeError("unsupported version of data format. Try updating hpaste to the latest version")
    if data.get('version.minor', 0) > current_format_version[1]:
        print('HPaste: Warning!! snippet has later format version than hpaste. Consider updating hpaste to the latest version')
    if data.get('signed', False):
        print('HPaste: Warning!! this snippet seem to be signed, but this version of HPaste has no idea how to check signatures! so signature check will be skipped!')

    # check accepted algtypes
    supportedAlgs = set()
    if houver1[0] == 15:
        supportedAlgs.add(0)
        supportedAlgs.add(1)
        supportedAlgs.add(2)  # WITH BIG WARNING!!!
    if houver1[0] >= 16:
        supportedAlgs.add(0)
        supportedAlgs.add(1)
        supportedAlgs.add(2)
    algtype = data['algtype']
    if algtype not in supportedAlgs:
        raise RuntimeError("algorithm type is not supported by this houdini version, :( ")

    # check hou version
    houver2 = data['houver']
    if not opt.getOption('hpaste.ignore_houversion_warning', False) and (houver1[0] != houver2[0] or houver1[1] != houver2[1]):
        print("HPaste: WARNING!! nodes were copied from a different houdini version: " + str(houver2))

    # check context
    context = getChildContext(hou_parent, houver1)
    if context != data['context']:
        raise InvalidContextError(hou_parent, data['context'])  # RuntimeError("this snippet has '%s' context" % data['context'])

    # check sum
    code = data['code'].encode('UTF-8')
    if hashlib.sha1(code).hexdigest() != data['chsum']:
        raise RuntimeError("checksum failed!")

    if paste_to_position:
        if houver1[0] >= 16:
            olditems = hou_parent.allItems()
        else:
            olditems = hou_parent.children()

    deserialize = getDeserializer(enctype=data.get('encryptionType', None), key=key, **(data.get('encryptionData', None) or {}))

    # do the work
    for hdaitem in data.get('hdaList', []):  # added in version 2.1
        hdacode = deserialize(hdaitem['code'])
        ntype = hdaitem['type']
        ncategory = hdaitem['category']
        if ignore_hdas_if_already_defined:
            nodeType = hou.nodeType(hou.nodeTypeCategories()[ncategory], ntype)
            if nodeType is not None:
                # well, that's already a bad sign, means it is installed
                continue

        fd, temppath = tempfile.mkstemp()
        try:
            with open(temppath, 'wb') as f:
                f.write(hdacode)
            for hdadef in hou.hda.definitionsInFile(temppath):
                hdadef.copyToHDAFile('Embedded')
            # hdadef.save('Embedded')
        finally:
            os.close(fd)

        if force_prefer_hdas:
            embhdas = [x for x in hou.hda.definitionsInFile("Embedded") if (x.nodeType().name() == ntype and x.nodeTypeCategory().name() == ncategory)]
            if len(embhdas) == 1:
                embhdas[0].setIsPreferred(True)

    # now nodes themselves
    if formatVersion == 1:
        code = binascii.a2b_qp(code)
    elif formatVersion >= 2:
        code = deserialize(code)
    else:
        raise RuntimeError("Very unexpected format version in a very unexpected place!")

    load_warnings = []
    if algtype == 0:
        # high security risk!!
        if hou.isUiAvailable():
            ok = hou.ui.displayMessage(
                "WARNING! The algorithm type used by the pasted snipped is legacy and present HIGH SECURITY RISK!\n be sure you TRUST THE SOURCE of the snippet!",
                ("CANCEL", "ok"), severity=hou.severityType.Warning, close_choice=0, title="SECURITY WARNING")
        else:
            ok = 0
            print("for now u cannot paste SECURITY RISK snippets in non-interactive mode")
        if ok != 1:
            return

        exec(code, {}, {'hou': hou, 'hou_parent': hou_parent})
    elif algtype == 1 or algtype == 2:
        # get temp file
        fd, temppath = tempfile.mkstemp()
        try:
            with open(temppath, "wb") as f:
                f.write(code)
            try:
                if algtype == 1:
                    hou_parent.loadChildrenFromFile(temppath)
                if algtype == 2:
                    try:
                        hou_parent.loadItemsFromFile(temppath)
                    except AttributeError:
                        print("WARNING!!! your hou version does not support algorithm used for copying, TRYING possibly partly backward-INCOMPATIBLE method!")
                        print("CHECK SCENE INTEGRITY")
                        hou_parent.loadChildrenFromFile(temppath)
            except hou.LoadWarning as e:
                msg = e.instanceMessage()
                print(msg)

                # truncate just for display with random number 253
                msgtrunc = False
                if len(msg) > 253:
                    msgtrunc = True
                    msg = msg[:253] + "..."
                load_warnings.append("There were warnings during load" + ("(see console for full message)" if msgtrunc else "") + "\n" + msg)
        finally:
            os.close(fd)
    else:
        raise RuntimeError("algorithm type is not supported. Try updating hpaste to the latest version")

    if paste_to_position:
        # now collect pasted nodes
        if houver1[0] >= 16:
            newitems = [x for x in hou_parent.allItems() if x not in olditems]
        else:
            newitems = [x for x in hou_parent.children() if x not in olditems]

        if len(newitems) == 0:
            return
        # calc center
        cpos = hou.Vector2()
        bbmin = hou.Vector2()
        bbmax = hou.Vector2()
        cnt = 0
        for item in newitems:
            cnt += 1
            pos = item.position()
            cpos += pos
            for i in [0, 1]:
                if pos[i] > bbmax[i] or cnt == 1:
                    bbmax[i] = pos[i]
                if pos[i] < bbmin[i] or cnt == 1:
                    bbmin[i] = pos[i]

        cpos = cpos / cnt
        cpos[1] = bbmax[1]
        if override_network_position is None:
            offset = ne.cursorPosition() - cpos
        else:
            offset = override_network_position - cpos
        for item in newitems:
            if houver1[0] >= 16 and item.parentNetworkBox() in newitems:
                continue
            item.move(offset)

    if len(load_warnings) > 0:
        raise RuntimeWarning('snippet loaded with following warnings:\n' + '\n'.join(load_warnings))
