levelhreshold = 2


def simpleLogger(s, level=1):
    if level < levelhreshold:
        return
    levels = ['VERBOSE', 'INFO', 'WARNING', 'ERROR', 'SUPER ERROR', 'OMEGA ERROR']
    if level < 0:
        level = 0
    elif level >= len(levels):
        level = len(levels) - 1
    print('%s: %s' % (levels[level], s))


def passLogger(s, level=1):
    pass


defaultLogger = simpleLogger
