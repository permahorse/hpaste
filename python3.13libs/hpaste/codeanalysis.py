import sys
import re

from .hpaste import stringToData, WrongKeyError


cheader = re.compile(b'070707[0-7]{6}[0-7]{6}'
                     b'(?P<mode>[0-7]{6})'
                     b'(?P<uid>[0-7]{6})'
                     b'(?P<gid>[0-7]{6})'
                     b'(?P<nlink>[0-7]{6})'
                     b'(?P<rdev>[0-7]{6})'
                     b'(?P<mtime>[0-7]{11})'
                     b'(?P<namesize>[0-7]{6})'
                     b'(?P<filesize>[0-7]{11})')

ncheader = re.compile(b'(?P<lic>Hou[LN]C)\x1a'
                      b'[0-7]{5}'
                      b'(?P<cpionamelen>[0-9a-fA-F]{5})'
                      b'(?P<time>[0-9a-fA-F]{9})'
                      b'(?P<cpionamehash>[0-9a-fA-F]{9})')

pyimports = re.compile(br'(?:from(?:\s|\\\s)+'
                       br'(?P<from>\w+(?:(?:\\\n\s*)?\.(?:\\\n\s*)?\w+)*)'
                       br'(?:\s|\\\s)+)?'
                       br'import(?:\s|\\\s)+'
                       br'(?P<imp>\w+(?:(?:\\\n\s*)?\.(?:\\\n\s*)?\w+)*(?:(?:\s|\\\s)*,(?:\s|\\\s)*\w+(?:(?:\\\n\s*)?\.(?:\\\n\s*)?\w+)*)*)', re.MULTILINE)  # TODO: this doesnt capture unicode imports as we work with binary


nodeinit = re.compile(b'(\\w+(?:/\\w+)*)\\.init\0(?:type\\s+=\\s+(\\w+))?')

statmeta = re.compile(br'stat\s*'
                      br'\{'
                      br'\s*create\s+(?P<create>\d+)\n'
                      br'\s*modify\s+(?P<modify>\d+)\n'
                      br'\s*author\s+(?P<author>.+)@(?P<hostname>.+)\n'
                      br'\s*access\s+(?P<access>\d+)\n'
                      br'\s*\}', re.MULTILINE)

sesilic = re.compile(br'(?P<sesilic>alias\s+(?:-u\s+)?\'?__sesi_license__\'?\s+(?:\'\s*)?\{(?P<lic>[^}]*)\}(?:\'\s*)?)', re.MULTILINE)


def _lic_type_from_code(code, data):
    # type: (bytes, dict) -> str
    lic = 'unknown'
    if cheader.match(code):
        lic = 'Commercial'
    else:
        match = ncheader.match(code)
        if match:
            lic = 'Non Commercial' if match.group('lic') == 'HouNC' else 'Limited Commercial'
    data['license'] = lic
    return lic


def _scan_for_python_imports(code, data):
    # type: (bytes, dict) -> set[str]
    imports = set()
    for match in pyimports.finditer(code):
        pref = None
        if match.group('from'):
            pref = match.group('from').decode('UTF-8')
            pref = re.sub(r'(?:\s|\n|\\\s)+', '', pref, re.MULTILINE)

        imps = re.sub(r'(?:\s|\n|\\\s)+', '', match.group('imp').decode('UTF-8'), re.MULTILINE).split(',')
        if pref:
            imps = ['.'.join((pref, imp)) for imp in imps]
        imports.update(imps)
    data['imports'] = imports
    return imports


def _scan_for_nodes(code, data):
    # type: (bytes, dict) -> list[(str, str)]
    """
    this is a very approximate crude method
    """
    nodes = []

    lic = _lic_type_from_code(code, {})
    if lic == 'unknown':
        raise RuntimeError('unknown license type')
    elif lic == 'Commercial':
        header = cheader
    else:
        header = ncheader
    for match in header.finditer(code):
        nmatch = nodeinit.match(code, pos=match.end())
        if nmatch:
            nodes.append((nmatch.group(1).decode('UTF-8'), nmatch.group(2).decode('UTF-8') if nmatch.group(2) else '<N/A>'))
    data['nodes'] = nodes
    return nodes


def _scan_for_misc(code, data):
    # type: (bytes, dict) -> str
    match = sesilic.search(code)
    if not match:
        return ''

    res = match.group('lic').decode('UTF-8')
    data['license.alias'] = res
    return res


def _scan_for_authors_dates(code, data):
    # type: (bytes, dict) -> tuple[set[tuple[str, str]], tuple[tuple[int, int], tuple[int, int]]]
    authors = set()
    min_c_time = sys.maxsize
    min_m_time = sys.maxsize
    max_c_time = 0
    max_m_time = 0
    for match in statmeta.finditer(code):
        authors.add((match.group('author').decode('UTF-8'), match.group('hostname').decode('UTF-8')))
        ctime = int(match.group('create'))
        mtime = int(match.group('modify'))
        min_c_time = min(min_c_time, ctime)
        max_c_time = max(max_c_time, ctime)
        min_m_time = min(min_m_time, mtime)
        max_m_time = max(max_m_time, mtime)
    data['authors'] = authors
    data['nctimes'] = (min_c_time, max_c_time)
    data['nmtimes'] = (min_m_time, max_m_time)
    return authors, ((min_c_time, max_c_time), (min_m_time, max_m_time))


def generate_report_data(s, key=None):
    data, deserializer = stringToData(s, key)
    if data['version'] < 2:
        raise NotImplementedError('legacy snippet formats are not supported')

    if deserializer is None:
        return {'error': 'cannot deserialize data, probably encryption key was not provided'}

    try:
        code = deserializer(data['code'].encode('UTF-8'))  # type: bytes
    except WrongKeyError:
        return {'error': 'cannot deserialize data, wrong encryption key provided'}

    return generate_report_data_for_code(code)


def generate_report_data_for_code(code):
    info = {}

    _lic_type_from_code(code, info)
    _scan_for_python_imports(code, info)
    _scan_for_nodes(code, info)
    _scan_for_authors_dates(code, info)
    _scan_for_misc(code, info)

    return info


def _test_scan_for_python_imports():
    text = br'''something
    from ass.pop\
    import\
        mouth , \
        wowus.\
        titus
andmorethings'''
    test = _scan_for_python_imports(text, {})
    assert test == {'ass.pop.mouth', 'ass.pop.wowus.titus'}, test


def _test_scan_for_nodes():
    text1 = b'''HouLC\x1a1033600bbf0626e4915092bb9909geo1/merge11.parm\0{
version 0.8
}
HouLC\x1a1033600bbb0626e4915076ac4ae7geo1/merge11.userdata\0\0\0\0\1\0
___Version___\0\0\0\x03\0\x0818.5.408HouLC\x1a1033600bbc0626e491507277fc71geo1/group9.init\0type = groupcreate
matchesdef = 0
HouLC\x1a1033600bbd0626e4915015968140geo1/group9.def\0sopflags sopflags = '''

    text2 = b'''0707070000010000000006660000000000000000010000001423446663300005300000000036vellumsolver1/dopnet1/forces/popwind1.init\0type = popwind
matchesdef = 1
0707070000010000000006660000000000000000010000001423446663300005200000000703vellumsolver1/dopnet1/forces/popwind1.def\0comment ""
position -0.286053 3.28347
connectornextid 1'''
    test = _scan_for_nodes(text1, {})
    assert test == [('geo1/group9', 'groupcreate')], test

    test = _scan_for_nodes(text2, {})
    assert test == [('vellumsolver1/dopnet1/forces/popwind1', 'popwind')], test


def _test_scan_author_meta():
    text = b'''outputsNamed3
{
}
inputsNamed3
{
}
inputs
{
}
stat
{
  create 1656665358
  modify 1656665364
  author joey@lucy
  access 0777
}
color UT_Color RGB 0.8 0.8 0.8 
delscript ""
exprlanguage hscript
end
0707070000010000000006660000000000000000010000001423273142300001500000000243python1.parm\0{
version 0.8'''
    test = _scan_for_authors_dates(text, {})
    assert test == ({('joey', 'lucy')}, ((1656665358, 1656665358), (1656665364, 1656665364))), test


if __name__ == '__main__':
    _test_scan_for_python_imports()
    _test_scan_for_nodes()
    _test_scan_author_meta()
    print('all tests are fine')
