import urllib2
import json
import re

from ..webclipboardbase import WebClipBoardBase
from .. import hpasteoptions as opt


class GitHub(WebClipBoardBase):
    def __init__(self):
        #todo: make proper user agent
        self.__headers = {'User-Agent': 'HPaste'}

    @classmethod
    def speedClass(cls):
        return opt.getOption('hpasteweb.plugins.%s.speed_class'%cls.__name__,4)

    @classmethod
    def maxStringLength(self):
        return 10000000 #actually the service seem th be able to eat more, much more!

    def webPackData(self, s):
        if (not isinstance(s, str)):
            s = str(s)
        if (len(s) > self.maxStringLength()): raise RuntimeError("len of s it too big for web clipboard currently")
        data = {}
        data["description"] = "hpaste exchange snippet"
        data['public'] = False
        data['files'] = {'snippet.hou': {"content": s}}
        try:
            req = urllib2.Request(r'https://api.github.com/gists', json.dumps(data).encode('UTF-8'), headers=self.__headers)
            rep = urllib2.urlopen(req, timeout=30)
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + str(e.message))

        try:
            repdata = json.loads(rep.read())
        except:
            raise RuntimeError("server response cannot be parsed")

        # if (rep.getcode() != 201): raise RuntimeError("error code from web clipboard")
        rawurl=repdata["files"]["snippet.hou"]["raw_url"]
        #print(rawurl)
        repmatch=re.match(r'.*\/anonymous\/([^\/\.]+)\/raw\/([^\/\.]+)\/snippet\.hou',rawurl)
        if(repmatch is None):
            raise RuntimeError("unexpected clipboard url")
        id='-'.join((repmatch.group(1),repmatch.group(2)))

        return str(id)


    def webUnpackData(self, id):
        id=str(id)
        if('-' not in id):raise RuntimeError("bad wid format!")
        idparts=id.split('-')
        try:
            req = urllib2.Request(r"https://gist.githubusercontent.com/anonymous/"+idparts[0]+r"/raw/"+idparts[1]+r"/snippet.hou", headers=self.__headers)
            rep = urllib2.urlopen(req, timeout=30)
        except Exception as e:
            raise RuntimeError("error/timeout connecting to web clipboard: " + e.message)

        if (rep.getcode() != 200): raise RuntimeError("error code from web clipboard")

        repstring = rep.read()

        return repstring
