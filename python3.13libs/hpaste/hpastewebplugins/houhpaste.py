from urllib import request
from urllib.error import URLError, HTTPError
import json

from ..webclipboardbase import WebClipBoardBase, WebClipBoardWidNotFound
from .. import hpasteoptions as opt


class HPaste(WebClipBoardBase):
    def __init__(self):
        self.__headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}

    @classmethod
    def speedClass(cls):
        return opt.getOption('hpasteweb.plugins.%s.speed_class' % cls.__name__, 10)

    @classmethod
    def maxStringLength(cls):
        return 2**20

    @classmethod
    def urlopen(cls, url, timeout=30):
        try:
            rep = request.urlopen(url, timeout=timeout)
        except URLError as e:
            try:
                import certifi
                rep = request.urlopen(url, timeout=timeout, cafile=certifi.where())
            except ImportError:
                import ssl
                rep = request.urlopen(url, timeout=timeout, context=ssl._create_unverified_context())
                print("WARNING: connected with unverified context")
        return rep

    def webPackData(self, s: str) -> str:
        if len(s) > self.maxStringLength():
            raise RuntimeError("len of s it too big for web clipboard currently")

        s = s.encode('UTF-8')

        try:
            req = request.Request(r"https://hou-hpaste.herokuapp.com/documents", s, headers=self.__headers)
            rep = self.urlopen(req, timeout=30)
            repstring = rep.read()
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + repr(e))

        if rep.getcode() != 200:
            raise RuntimeError("error code from web clipboard")

        try:
            repson = json.loads(repstring)
            id = repson['key']
        except Exception as e:
            raise RuntimeError("Unknown Server responce: " + repr(e))

        assert isinstance(id, str)
        return id

    def webUnpackData(self, wid: str) -> str:
        # id = id.encode('UTF-8')
        try:
            req = request.Request(r"https://hou-hpaste.herokuapp.com/raw/" + wid, headers=self.__headers)
            rep = self.urlopen(req, timeout=30)
        except HTTPError as e:
            if e.code == 404:
                raise WebClipBoardWidNotFound(wid)
            raise RuntimeError("error connecting to web clipboard: " + repr(e))
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + repr(e))

        if rep.getcode() != 200:
            raise RuntimeError("error code from web clipboard")

        repstring = rep.read()

        return repstring.decode('UTF-8')
