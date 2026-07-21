
import urllib2
import socket
import re

from ..webclipboardbase import WebClipBoardBase
from .. import hpasteoptions as opt


class TermBin(WebClipBoardBase):
    def __init__(self):
        pass

    @classmethod
    def speedClass(cls):
        return opt.getOption('hpasteweb.plugins.%s.speed_class'%cls.__name__,4)

    @classmethod
    def maxStringLength(self):
        return 1048000

    def webPackData(self, s):
        if(not isinstance(s,str)):
            s=str(s)

        if (len(s) > self.maxStringLength()): raise RuntimeError("len of s it too big for web clipboard currently")
        try:
            skt=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            skt.settimeout(30)
            skt.connect((r'termbin.com',9999))
            skt.sendall(s)
            repurl=skt.recv(256)
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + str(e.message))


        # if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        # like http://termbin.com/8onr
        repmatch=re.match(r'http:\/\/termbin\.com\/(.+)',repurl)
        if(repmatch is None):
            raise RuntimeError("unexpected clipboard url")
        id=repmatch.group(1)

        return str(id)


    def webUnpackData(self, id):
        id=str(id)


        try:
            req = urllib2.Request(r"http://termbin.com/"+id)
            rep = urllib2.urlopen(req, timeout=30)
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + e.message)

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        repstring = rep.read()

        return repstring
