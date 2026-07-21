#!/usr/bin/env python
"""
this file is par of https://github.com/pedohorse/hip-meta-stripper repository
"""
from __future__ import print_function
import sys
import re
from copy import copy
import time
from getpass import getuser  # for sanity check

try:
    from typing import Union, Optional
except ImportError:
    pass

########################
# SOME GLOBAL SETTINGS #
########################

print_debug = 0

simple_remaps = {
    b'.variables': [
        [re.compile(b'set -g HIP = (.*?)$', re.MULTILINE),            b'set -g HIP = /dev'],
        [re.compile(b'set -g HIPFILE = (.*?)$', re.MULTILINE),        b'set -g HIPFILE = /dev/null'],
        [re.compile(b'set -g POSE = (.*?)$', re.MULTILINE),           b'set -g POSE = /dev/null'],
        [re.compile(b'set -g _HIP_SAVETIME = (.*?)$', re.MULTILINE),  b'set -g _HIP_SAVETIME = \'Fri Aug 29  2:14:00 1997\'']
    ]
}

do_spoof_cpio_timestamp = True
do_spoof_stat_timestamp = True
spoof_timestamp = 872838840
spoof_user = b'nobody'
spoof_host = b'nowhere'


##########################
# END OF GLOBAL SETTINGS #
##########################


class buffer23(object):
    def __init__(self, text):
        if sys.version_info.major == 2:
            self.__py = 2
            self.__inner = buffer(text)
        else:
            self.__py = 3
            self.__inner = memoryview(text)

    def __getitem__(self, val):
        if isinstance(val, int):
            return self.__inner[val]
        if isinstance(val, slice):
            if val.step not in (None, 1):
                raise NotImplemented('not implemented for steps !=1')
            new = copy(self)
            if self.__py == 2:
                new.__inner = buffer(self.__inner, val.start or 0, (len(self.__inner) if val.stop is None else val.stop) - (val.start or 0))
            else:
                new.__inner = self.__inner.__getitem__(val)
            return new
        raise RuntimeError('wtf?')

    def __len__(self):
        return len(self.__inner)

    def tobytes(self):
        if self.__py == 2:
            return bytes(self.__inner)
        else:
            return self.__inner.tobytes()

    def get_inner(self):  # type: () -> Union[memoryview, buffer]
        """
        use MUST be read-only
        """
        return self.__inner


def clean_meta(filetext):  # type: (bytes) -> bytes
    """
    this expects filetext to start with a correct block header
    """
    if filetext.startswith(b'070707'):
        return clean_meta_c(filetext)
    else:
        return clean_meta_nc(filetext)


def clean_meta_c(filetext):  # type: (bytes) -> bytes
    cpio_rgx = re.compile(br'070707(?P<crap>\d{42})(?P<mtime>\d{11})(?P<namesize>\d{6})(?P<bodysize>\d{11})', re.M)
    stat_rgx = re.compile(b'|'.join((br'(?P<stat>stat\s*\{(?P<statinner>[^}]*)\})',
                                     br'(?P<sesilic>alias\s+(?:-u\s+)?\'?__sesi_license__\'?\s+(?:\'\s*)?\{([^}]*)\}(?:\'\s*)?)'
                                     )), re.M)

    def cleaninsides(text, blockname=None):
        blocks = []
        total_size = 0
        orig_size = len(text)
        remaps = []
        rgx = stat_rgx
        if blockname in simple_remaps:
            remaps = simple_remaps[blockname]
            rgx = re.compile(b'|'.join((
                stat_rgx.pattern,
                br'(?P<simple_remap>%s)' % b'|'.join(
                    x[0].pattern for x in remaps
                )
            )), re.M)
        while True:
            match = rgx.search(text.get_inner())
            if match is None:
                total_size += len(text)
                blocks.append(text)
                break
            preblock = text[:match.start()]
            blocks.append(preblock)
            total_size += len(preblock)
            if match.group('stat') is not None:
                statinner = match.group('statinner')
                if do_spoof_stat_timestamp:
                    statinner = re.sub(br'(?<=create\s)\s*\d+', spoof_timestamp_bytes10, statinner)
                    statinner = re.sub(br'(?<=modify\s)\s*\d+', spoof_timestamp_bytes10, statinner)
                statinner = re.sub(br'(?<=author\s)\s*[\w@.]+', spoof_userhost, statinner)
                blocks.append(b'stat\n{%s}' % statinner)
                total_size += len(blocks[-1])
            elif match.group('sesilic'):
                pass  # just skip that shit
            elif len(remaps) > 0:
                for remap in remaps:
                    if remap[0].match(match.group(0)):
                        blocks.append(remap[1])
                        total_size += len(blocks[-1])
                        break
            text = text[match.end():]
        return blocks, total_size - orig_size

    def search_block(text, blockname=None):  # type: (buffer23, Optional[bytes]) -> (list, int)
        blocks = []
        total_size_shift = 0
        while True:
            match = cpio_rgx.search(text.get_inner())
            if match is None:
                textblocks, shift = cleaninsides(text[:], blockname)
                blocks.extend(textblocks)
                total_size_shift += shift
                break
            textblocks, shift = cleaninsides(text[:match.start()], blockname)
            blocks.extend(textblocks)
            total_size_shift += shift

            m_bodysize = int(match.group('bodysize'), 8)
            blockend = match.end() + int(match.group('namesize'), 8) + m_bodysize
            childblocks, shift = search_block(text[match.end():blockend], text[match.end():match.end() + int(match.group('namesize'), 8) - 1].tobytes())
            mtime = spoof_timestamp_bytes08 if do_spoof_cpio_timestamp else match.group('mtime')
            blocks.append(b'070707' + match.group('crap') + mtime + match.group('namesize') + b'%011o' % (m_bodysize + shift,))
            total_size_shift += shift
            blocks.extend(childblocks)
            text = text[blockend:]
        return blocks, total_size_shift

    spoof_timestamp_bytes10 = b'%d' % spoof_timestamp
    spoof_timestamp_bytes08 = b'%011o' % spoof_timestamp
    spoof_userhost = b'%s@%s' % (spoof_user, spoof_host)
    textview = buffer23(filetext)
    blocks, _ = search_block(textview)
    return b''.join(x.tobytes() if isinstance(x, buffer23) else x for x in blocks)


def _cycle_pattern(pattern, length):  # type: (bytes, int) -> bytes
    pattern_len = len(pattern)
    if length <= pattern_len:
        return pattern[:length]
    return (pattern*(int(length//pattern_len) + 1))[:length]


def clean_meta_nc(filetext):  # type: (bytes) -> bytes
    """
    this tries to cleanup metadata in NC files, but does it through simple pattern analysis as opposed to block analysis, as with commercial files
    """
    # TODO: regex below relies on create-modify-author strict order
    loose_stat_rgx = re.compile(br'Hou[NL]C\x1a[0-7]{5}[0-9a-fA-F]{5}(?P<htime>[0-9a-fA-F]{9})[0-9a-fA-F]{9}'
                                br'(?:'
                                br'(?:\w|/)+\.def' b'\0'
                                b'.*?' 
                                br'(?:'
                                br'(?P<stat>stat\s*\{[^}]*'
                                br'\s*create\s+(?P<create>\d+)\n'
                                br'\s*modify\s+(?P<modify>\d+)\n'
                                br'\s*author\s+(?P<author>[^}]+)@(?P<hostname>[^}\n]+)\n'
                                br'[^}]*\})'
                                br'|.(?=Hou[NL]C\x1a)'
                                br')'
                                br')?', re.M | re.DOTALL)

    spoof_timestamp_s = b'0' + str(spoof_timestamp).encode('UTF-8')
    spoof_timestamp_hs = '{:09x}'.format(spoof_timestamp).encode('UTF-8')
    blocks = []
    offset = 0
    for match in loose_stat_rgx.finditer(filetext):
        if do_spoof_cpio_timestamp:
            blocks.append(filetext[offset:match.start('htime')])
            blocks.append(spoof_timestamp_hs)
            offset = match.end('htime')
        if match.group('stat') is None:
            continue
        if do_spoof_stat_timestamp:
            blocks.append(filetext[offset:match.start('create')])
            blocks.append(_cycle_pattern(spoof_timestamp_s, len(match.group('create'))))
            blocks.append(filetext[match.end('create'):match.start('modify')])
            blocks.append(_cycle_pattern(spoof_timestamp_s, len(match.group('modify'))))
            offset = match.end('modify')
        blocks.append(filetext[offset:match.start('author')])
        blocks.append(_cycle_pattern(spoof_user, len(match.group('author'))) + b'@' +
                      _cycle_pattern(spoof_host, len(match.group('hostname')))
                      )
        offset = match.end('stat')
        blocks.append(filetext[match.end('hostname'):offset])

    if offset == 0:
        return filetext

    blocks.append(filetext[offset:])
    result = b''.join(blocks)
    # sanity check
    if (getuser().encode('UTF-8') + b'@') in blocks:
        print('metaclean WARNING: username still detected in nodecode!')
    return result


def clean_file(file_in, file_out):
    with open(file_in, 'rb') as f:
        text = f.read()
    _stt = time.time()
    text = clean_meta(text)
    # first check if there are any non-commercial parts inside - just skip that file
    # cuz we cannot find non-commercial block borders
    if re.search(br'Hou[NL]C\x1a[0-9a-fA-F]{28}', text):
        raise RuntimeError('non-commercial blocks found! cannot clean metadata')
    if print_debug > 0:
        print('metaclean took %g sec' % (time.time() - _stt))
    with open(file_out, 'wb') as f:
        f.write(text)
    return 0


def _main():
    if len(sys.argv) not in [2, 3]:
        return 2
    return clean_file(sys.argv[1], sys.argv[-1])


if __name__ == '__main__':
    sys.exit(_main() or 0)
