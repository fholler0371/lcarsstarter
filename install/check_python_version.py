import sys


MAIN_VERSION = 3
SUB_VERSION = 11

FACTOR = 1000

ver: tuple = sys.version_info

if MAIN_VERSION * FACTOR + SUB_VERSION <= ver.major * FACTOR + ver.minor:
    #python version ist zu klein
    sys.exit(-1)
