import urllib2
import re

from ..webclipboardbase import WebClipBoardBase
from .. import hpasteoptions as opt


class IX(WebClipBoardBase):
    def __init__(self):
        pass

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
            req = urllib2.Request(r"http://ix.io", 'f:1='+s)
            rep = urllib2.urlopen(req, timeout=30)
            repstring = rep.read()
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + str(e.message))

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        #repstring is in form 'http://sprunge.us/iADC\n'
        repmatch=re.match(r'http:\/\/ix\.io\/([^\/\.\n]+)\n?$',repstring)
        if(repmatch is None):
            raise RuntimeError("Unrecognized server response")
        id=repmatch.group(1)

        return str(id)


    def webUnpackData(self, id):
        id=str(id)
        try:
            req = urllib2.Request(r"http://ix.io/" + id)
            rep = urllib2.urlopen(req, timeout=30)
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + e.message)

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        repstring = rep.read()

        return repstring[:-1]if repstring[-1]=='\n' else repstring #there is \n in the end...
