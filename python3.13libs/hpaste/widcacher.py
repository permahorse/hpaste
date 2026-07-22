class WidCacher(object):
    _instance = None

    def __init__(self, maxsize=8):
        self.__maxsize = max(maxsize, 1)
        self.__cachedict = {}
        self.__cachequeue = []

    def __contains__(self, item):
        return item in self.__cachedict

    def __getitem__(self, item):
        return self.__cachedict[item]

    def __setitem__(self, key, value):
        if key in self.__cachequeue:
            self.__cachequeue.remove(key)
        if len(self.__cachequeue) >= self.__maxsize:
            for el in self.__cachequeue[self.__maxsize - 1:]:
                del self.__cachedict[el]
            self.__cachequeue = self.__cachequeue[:self.__maxsize - 1]
        self.__cachequeue.insert(0, key)
        self.__cachedict[key] = value

    def __len__(self):
        return len(self.__cachequeue)

    def maxSize(self):
        return self.__maxsize

    def clear(self):
        self.__cachedict = {}
        self.__cachequeue = []

    @classmethod
    def globalInstance(cls):
        if cls._instance is None:
            cls._instance = WidCacher()
        return cls._instance
