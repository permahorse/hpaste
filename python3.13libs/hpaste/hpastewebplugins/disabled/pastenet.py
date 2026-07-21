import urllib2
import re

from ..webclipboardbase import WebClipBoardBase
from .. import hpasteoptions as opt


class PasteNet(WebClipBoardBase):
    def __init__(self):
        self.__host = r'http://pastenet.com/'
        self.__headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}

    @classmethod
    def speedClass(cls):
        return opt.getOption('hpasteweb.plugins.%s.speed_class'%cls.__name__,3)

    @classmethod
    def maxStringLength(self):
        return 65000 #very small!

    def webPackData(self, s):
        if (not isinstance(s, str)):
            s = str(s)
        if (len(s) > self.maxStringLength()): raise RuntimeError("len of s it too big for web clipboard currently")

        try:
            req = urllib2.Request(self.__host+"index.php", "title=anus&visibility=1&paste_expire_date=1W&format=text&paste_data=###===DATASTART===###"+s+"###===DATAEND===###", headers=self.__headers)
            rep = urllib2.urlopen(req, timeout=30)
            repstring = rep.read()
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + str(e.message))

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")
        #
        repmatch=re.search(r'value="http:\/\/pastenet\.com\/([^\/\.]*)\/*"',repstring)
        if(repmatch is None):
            raise RuntimeError("unexpected clipboard server response")
        id=repmatch.group(1)

        return str(id)


    def webUnpackData(self, id):
        id=str(id)
        try:
            req = urllib2.Request(self.__host + "paste.php?download&id=" + id, headers=self.__headers)
            rep = urllib2.urlopen(req, timeout=30)
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + e.message)

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        repstring = rep.read()
        datastart = repstring.find('###===DATASTART===###')
        if (datastart == -1):
            #print(repstring)
            raise RuntimeError("data is corrupted")
        dataend = repstring.rfind('###===DATAEND===###')
        if (dataend == -1): raise RuntimeError("data end is corrupted")

        s = repstring[datastart + 21:dataend]
        return s
