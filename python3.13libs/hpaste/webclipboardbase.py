# TODO: move this class to hpastewebplugins

class WebClipBoardError(RuntimeError):
    pass


class WebClipBoardWidNotFound(WebClipBoardError):
    def __init__(self, wid):
        self.wid = wid


class WebClipBoardBase(object):

    @classmethod
    def speedClass(self):
        """
        :return: int: speed class of the web plugin (0-9)
        """
        raise NotImplementedError()

    @classmethod
    def maxStringLength(self):
        """
        Keep in mind - this is about ascii string, so it should be equal to max data size in bytes
        :return: max string length
        """
        raise NotImplementedError()

    def webPackData(self, s: str) -> str:
        raise NotImplementedError()

    def webUnpackData(self, s: str) -> str:
        raise NotImplementedError()
