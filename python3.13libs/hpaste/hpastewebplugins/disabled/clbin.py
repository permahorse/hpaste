import urllib2
import re

from ..webclipboardbase import WebClipBoardBase
from .. import hpasteoptions as opt

class Clbin(WebClipBoardBase):
    def __init__(self):
        self.__headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}

    @classmethod
    def speedClass(cls):
        return opt.getOption('hpasteweb.plugins.%s.speed_class'%cls.__name__,4)

    @classmethod
    def maxStringLength(self):
        return 1000000 #approx

    def webPackData(self, s):
        if (not isinstance(s, str)):
            s = str(s)
        if (len(s) > self.maxStringLength()): raise RuntimeError("len of s it too big for web clipboard currently")

        try:
            req = urllib2.Request(r"https://clbin.com", 'clbin='+s, headers=self.__headers)
            rep = urllib2.urlopen(req, timeout=30)
            repstring = rep.read()
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + str(e.message))

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        #repstring is in form 'http://sprunge.us/iADC\n'
        repmatch=re.match(r'https:\/\/clbin\.com\/([^\/\.\n]+)\n?$',repstring)
        if(repmatch is None):
            raise RuntimeError("Unrecognized server response")
        id=repmatch.group(1)

        return str(id)


    def webUnpackData(self, id):
        id=str(id)
        try:
            req = urllib2.Request(r"https://clbin.com/" + id, headers=self.__headers)
            rep = urllib2.urlopen(req, timeout=30)
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + e.message)

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        repstring = rep.read()

        return repstring[:-1]if repstring[-1]=='\n' else repstring #there is \n in the end...
