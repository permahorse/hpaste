class CollectionInconsistentError(Exception):
    # raise this when there are incinsistencies detected with a collection
    def __init__(self, message=''):
        super(CollectionInconsistentError, self).__init__('Collection Inconsistent Error: ' + message)


class CollectionSyncError(Exception):
    # raise this when collection syncronisation failed
    # but local collection is still valid, and remote did not show signs of inconsistency
    # when this is raised during some action, the collection should remain in the same state as before the action
    def __init__(self, message=''):
        super(CollectionSyncError, self).__init__('Collection Sync Error: ' + message)


class CollectionItemInvalidError(Exception):
    # item was destroyed, but still addressed
    def __init__(self, message='Maybe it was removed from collection.'):
        super(CollectionItemInvalidError, self).__init__('Item was invalidated: ' + message)


class CollectionAccessError(Exception):
    # item is readonly but someone tries to modify it
    def __init__(self, message='access violation'):
        super(CollectionAccessError, self).__init__('Access violation attempt: ' + message)  # TODO: make universal access checking thingie, and access error exceptions hierarchy


class CollectionReadonlyError(CollectionAccessError):
    # item is readonly but someone tries to modify it
    def __init__(self, message='Collection is readonly!'):
        super(CollectionReadonlyError, self).__init__('Readonly access violation attempt: ' + message)


class CollectionItemReadonlyError(CollectionAccessError):
    # item is readonly but someone tries to modify it
    def __init__(self, message='Item is readonly!'):
        super(CollectionItemReadonlyError, self).__init__('Readonly access violation attempt: ' + message)


class CollectionItem(object):
    class AccessType:
        private = 0
        public = 1

    def __init__(self, collection, name, description, id, access=AccessType.private, readonly=False, metadata=None):
        self._collection = collection
        self._name = name  # Name
        self._desc = description  # Description
        self._id = id  # ID inside collection
        self._access = access
        self._readonly = readonly
        self._meta = metadata  # Metadata
        self.__valid = True

        self.__cache = None
        self.__cacheNeedsUpdate = True

    # wid is not stored cuz it may be generated dynamically

    def name(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._name

    def description(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._desc

    def id(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._id

    def access(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._access

    def readonly(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._readonly

    def metadata(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._meta

    def generatePublicWid(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._collection.genWid(self)

    def content(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        if self.__cacheNeedsUpdate:
            self.__cache = self._collection.getContent(self)
            self.__cacheNeedsUpdate = False
        return self.__cache

    def collection(self):
        if not self.__valid:
            raise CollectionItemInvalidError()
        return self._collection

    def setName(self, newname):
        if not self.__valid:
            raise CollectionItemInvalidError()
        if self._readonly:
            raise CollectionItemReadonlyError()
        self._collection.changeItem(self, newName=newname)

    def setContent(self, newcontent):
        if not self.__valid:
            raise CollectionItemInvalidError()
        if self._readonly:
            raise CollectionItemReadonlyError()
        self._collection.changeItem(self, newContent=newcontent)
        self.__cacheNeedsUpdate = True

    def setDescription(self, newdescription):
        if not self.__valid:
            raise CollectionItemInvalidError()
        if self._readonly:
            raise CollectionItemReadonlyError()
        self._collection.changeItem(self, newDescription=newdescription)

    def setAccess(self, newaccess):
        if not self.__valid:
            raise CollectionItemInvalidError()
        if self._readonly:
            raise CollectionItemReadonlyError()
        self._collection.changeItem(self, newAccess=newaccess)

    def changeMetadata(self, metadataChanges):
        if not self.__valid:
            raise CollectionItemInvalidError()
        if self._readonly:
            raise CollectionItemReadonlyError()
        self._collection.changeItem(self, metadataChanges=metadataChanges)

    def removeSelf(self):
        # WARNING! item will be invalidated if removed!
        if not self.__valid:
            raise CollectionItemInvalidError()
        if self._readonly:
            raise CollectionItemReadonlyError()
        self._collection.removeItem(self)

    def isValid(self):
        return self.__valid

    def invalidate(self):
        self.__valid = False

    def dirtyContentCache(self):
        self.__cache = None
        self.__cacheNeedsUpdate = True


class CollectionBase(object):
    def __init__(self):
        # Deriving classes should establish connections to their sources here
        pass

    def name(self):
        # should return some kind of readable identifier for user to see
        raise NotImplementedError('Abstract method')

    def list(self):
        # this should produce list of snippets in the collection
        # the list should be a tuple of CollectionItem-s
        # note, that id is not a wid,
        raise NotImplementedError('Abstract method')

    def reinit(self):
        # this method should completely reread everything
        # rendering all existing items invalid
        raise NotImplementedError('Abstract method')

    def readonly(self):
        raise NotImplementedError('Abstract method')

    def genWid(self, item):
        # this should generate hpaste compatible wid, that does not require collections to work
        # collections can be separated from public wids, so creating a public wid is extra functionality
        raise NotImplementedError('Abstract method')

    def getContent(self, item):
        # this should bring the raw content of the collection item.
        raise NotImplementedError('Abstract method')

    def changeItem(self, item, newName=None, newDescription=None, newContent=None, newAccess=None, metadataChanges=None):
        # change an item
        raise NotImplementedError('Abstract method')

    def addItem(self, desiredName, description, content, access=CollectionItem.AccessType.private, metadata=None):
        # add a new item
        # should return CollectionItem
        raise NotImplementedError('Abstract method')

    def removeItem(self, item):
        # remove existing item
        raise NotImplementedError('Abstract method')
