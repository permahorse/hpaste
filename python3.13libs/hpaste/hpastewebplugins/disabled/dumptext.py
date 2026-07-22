import urllib2
import re

from ..webclipboardbase import WebClipBoardBase
from .. import hpasteoptions as opt

class DumpText(WebClipBoardBase):
    def __init__(self):
        self.__host = r"http://dumptext.com/"

    @classmethod
    def speedClass(cls):
        return opt.getOption('hpasteweb.plugins.%s.speed_class'%cls.__name__,2)

    @classmethod
    def maxStringLength(self):
        return 999000

    def webPackData(self, s):
        '''
        this function packs s into some internetclipboard, u r responsible for that s is web-acceptable
        :param s: string, cool for web
        :return: string id for that sketchy site
        '''

        # approximate limit
        if (not isinstance(s, str)):
            s = str(s)
        if (len(s) > self.maxStringLength()): raise RuntimeError("len of s it too big for web clipboard currently")

        try:
            req = urllib2.Request(self.__host, "submit=Dump&exposure=private&expiration=4&syntax=text&paste=" + "###===DATASTART===###" + s + "###===DATAEND===###")
            rep = urllib2.urlopen(req, timeout=30)
            repstring = rep.geturl()
        except Exception as e:
            raise RuntimeError("timeout connecting to web clipboard: " + e.message)
        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        # at this point repstring should be of this form http://dumptext.com/YI6dQ8FE
        repmatch=re.match(r'http:\/\/dumptext\.com\/([^\/\.]*)$',repstring)
        if(repmatch is None):
            raise RuntimeError("unexpected clipboard server response")
        id=repmatch.group(1)

        return str(id)

    def webUnpackData(self, id):
        id=str(id)
        try:
            req = urllib2.Request(self.__host + id + r'/raw')
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
