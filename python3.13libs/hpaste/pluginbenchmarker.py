import hpastewebplugins
import hpasteweb as hw
import random
import time
from pprint import pprint


def doTest(cycles=1):
    pluginlist = [x for x in hpastewebplugins.pluginClassList]
    ts = ''
    for i in range(50000): ts += chr(random.randint(ord('A'), ord('Z')))
    # s is 50 kb
    times = {}
    for cycle in range(cycles):
        for i in range(3):
            if i == 0:
                s = ts
            elif i == 1:
                s = ts * 10
            else:
                s = ts * 50

            for plug in pluginlist:
                if plug.__name__ not in times:
                    times[plug.__name__] = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]  # up,down,count
                try:
                    t1 = time.time()  # we'd better use time.clock() - but it's behaviour is too platform-dependent!
                    id = hw.webPack(s, [plug.__name__])
                    t2 = time.time()
                    ss = hw.webUnpack(id)
                    t3 = time.time()
                    if ss != s:
                        raise RuntimeError("test failed")
                    print('%s in progress #%d: %s' % (plug.__name__, i, str((t2 - t1, t3 - t2))))
                    times[plug.__name__][i][0] += t2 - t1
                    times[plug.__name__][i][1] += t3 - t2
                    times[plug.__name__][i][2] += 1
                except:
                    pass
            time.sleep(10)

    # totaltimes={}
    # for k in times:
    #     if k not in totaltimes:totaltimes[k]=0
    print('------------------------------\n')
    for k in times:
        print("%s :" % k)
        for i in range(3):
            if times[k][i][2] == 0:
                print("\t FAILED")
            else:
                print("\t %f :: %f" % (times[k][i][0] / times[k][i][2], times[k][i][1] / times[k][i][2]))
    return times
