import urllib2
import urllib

import random
import base64

from ..webclipboardbase import WebClipBoardBase
from .. import hpasteoptions as opt

class WePaste(WebClipBoardBase):
    def __init__(self):
        self.__lastid = ''
        self.__host = r"http://www.wepaste.com/"

        self.__symbols = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def genId(self, size=16):
        if (not isinstance(size, int)): raise AttributeError("size must be int")
        if (size < 1): raise RuntimeError("improper size")
        if (size > 4096): raise RuntimeError("improper size, why??")

        lsmo = len(self.__symbols) - 1
        id = ''
        for i in range(size):
            id += self.__symbols[random.randint(0, lsmo)]
        return id

    @classmethod
    def speedClass(cls):
        return opt.getOption('hpasteweb.plugins.%s.speed_class'%cls.__name__,6)

    @classmethod
    def maxStringLength(self):
        return 8000000

    def webPackData(self, s):
        '''
        this function packs s into some internetclipboard, u r responsible for that s is web-acceptable
        :param s: string, cool for web
        :return: string id for that site
        '''
        if (not isinstance(s, str)):
            s = str(s)
        # approximate limit
        if (len(s) > self.maxStringLength()): raise RuntimeError("len of s it too big for web clipboard currently")

        id = self.genId()
        try:
            rep = urllib2.urlopen(self.__host + id, timeout=4)  # request the page so it's created
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + str(e.message))
        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")
        req = urllib2.Request(self.__host + id, ''.join(("expires=32&save=Savet%20it&emailaddress&send_email=0&content=","###===DATASTART===###",s,"###===DATAEND===###")))
        try:
            rep = urllib2.urlopen(req, timeout=30)
        except Exception as e:
            raise RuntimeError("timeout connecting to web clipboard: " + str(e.message))
        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        # reading back... do we need it? just to check that we pasted stuff properly
        repstring = rep.read()
        datastart = repstring.find('###===DATASTART===###')
        if (datastart == -1):
            #print(repstring)
            raise RuntimeError("data is corrupted")
        dataend = repstring.rfind('###===DATAEND===###')
        if (dataend == -1): raise RuntimeError("data end is corrupted")

        correct = repstring[datastart + 21:dataend]
        if (not correct): raise RuntimeError("web clipboard data check failed")

        #self.__lastid = "@".join((id, base64.urlsafe_b64encode(type(self).__name__)))  # why?
        self.__lastid = str(id)
        return self.__lastid

    def webUnpackData(self, id):

        # check that id is at least valid
        id = str(id)  # in case of unicode that we dont need
        #wid = str(wid)  # in case of unicode that we dont need
        #if (wid.count('@') != 1): raise RuntimeError('given wid is not a valid wid')
        #(id, cname) = wid.split('@')

        #cname = base64.urlsafe_b64decode(cname)
        #if (cname != type(self).__name__): raise RuntimeError("given id ")

        for c in id:
            if c not in self.__symbols:
                raise RuntimeError("id is invalid")
        try:
            rep = urllib2.urlopen(self.__host + id, timeout=30)
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
