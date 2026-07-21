from urllib import request, error
from .logger import defaultLogger as log


class ErrorReply(object):
    def __init__(self, code, headers=None, msg=''):
        if headers is None:
            headers = {}
        self.__headers = headers
        self.__code = code
        self.msg = msg

    def info(self):
        return self.__headers

    def read(self):
        return None


def urlopen_nt(req: request.Request, fallback_cert: int = 0) -> (int, object):
    """
    wrapper around urllib2.urlopen that does not throw HTTPError
    and does some additional things like falling back on SSL certs
    :param req:
    :param fallback_cert:  do not use
    :return:
    """
    code = -1
    rep = None
    # print req.get_full_url(), req.get_data(), fallback_cert
    try:
        if fallback_cert == 0:
            rep = request.urlopen(req)
        elif fallback_cert == 1:
            import certifi
            rep = request.urlopen(req, cafile=certifi.where())
        elif fallback_cert == 2:
            import ssl
            rep = request.urlopen(req, context=ssl._create_unverified_context())
            log("connected with unverified context", 2)
    except error.HTTPError as e:
        code = e.code
        rep = ErrorReply(code, e.headers, e.reason)
    except error.URLError as e:
        if fallback_cert < 2:
            return urlopen_nt(req, fallback_cert+1)
        else:
            raise

    if code == -1:
        code = rep.getcode()
    return code, rep
