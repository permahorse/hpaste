"""
this module is responsible for providing settings for hpaste and it's plugins
"""
import os
import json
import copy

if __name__ == '__main__':
    if 'HOUDINI_USER_PREF_DIR' not in os.environ:
        os.environ['HOUDINI_USER_PREF_DIR'] = r'D:\tmp'

settings_filename = os.path.normpath(os.path.join(os.environ.get('HOUDINI_USER_PREF_DIR', '~'), '.hpaste_options'))
default_options = {'hpaste': {}, 'hpasteweb': {}}

cached_data = None


class NonExistingOptionError(Exception):
    def __init__(self, message, lastvalidname, firstinvalidname):
        super(NonExistingOptionError, self).__init__(message)
        self.namepair = (lastvalidname, firstinvalidname)


class OptionTypeError(Exception):
    pass


def _readOptionsFile(filename=settings_filename):
    """
    This funciont is supposed to be used internally
    :param filename:
    :return:
    """
    global cached_data
    try:
        with open(filename, 'r') as f:
            cached_data = json.load(f)
    except IOError:  # as e:
        # errno,message = e.args
        # print("Error reading settings file, Error %d: %s"%(errno,message))
        # print("Using default options")
        if cached_data is None:
            cached_data = default_options
    return cached_data


def _writeOptionFile(data, filename=settings_filename):
    global cached_data
    cached_data = data
    try:
        with open(filename, 'w') as f:
            json.dump(cached_data, f, indent=4)
    except IOError as e:
        errno, message = e.args
        print("Error writing to settings file! Error %d: %s" % (errno, message))
        print("settings are not saved!")
        return False
    return True


def getOption(option_name, defaultval=None):
    data = _readOptionsFile()
    names = option_name.split('.')
    option = data
    namesofar = ''
    for name in names:
        try:
            option = option[name]
            namesofar += '.%s' % name
        except KeyError:
            if defaultval is None:
                raise NonExistingOptionError('Option %s has no suboption %s' % (namesofar, name) if len(namesofar) == 0 else "Option %s does not exist" % name, namesofar, name)
            else:
                return defaultval

    return copy.deepcopy(option)


def setOption(option_name, value):
    data = _readOptionsFile()

    names = option_name.split('.')
    option = data
    namesofar = ''
    for name in names[:-1]:
        try:
            option = option[name]
        except KeyError:
            option[name] = {}
            option = option[name]
        except TypeError:
            raise OptionTypeError('Option %s is %s' % (namesofar, type(option).__name__))

        namesofar += '.%s' % name

    try:
        option[names[-1]] = value
    except TypeError:
        raise OptionTypeError('Option %s is %s' % (namesofar, type(option).__name__))

    _writeOptionFile(data)


if __name__ == '__main__':
    # test
    from pprint import pprint

    pprint(getOption('hpaste'))
    pprint(getOption('hpasteweb'))
    pprint("----------")
    setOption('hpaste.testoption1', 132)
    setOption('hpaste.testsu.lolo.bebe.gof', 'sdfq')
    pprint(getOption('hpaste'))
    pprint(getOption('hpaste.testoption1'))
    pprint(getOption('hpaste.testsu'))
    pprint(getOption('hpaste.testsu.lolo'))
    pprint(getOption('hpaste.testsu.lolo.bebe'))
    pprint(getOption('hpaste.testsu.lolo.bebe.gof'))
    pprint("-----------")
    pprint(getOption('hpaste.testsu.lolo.bebe.gos', 'default'))
    pprint(getOption('hpasteweb.cbin.speed_class', 4))
