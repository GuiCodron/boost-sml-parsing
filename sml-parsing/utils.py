from pprint import pprint
import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def epprint(*args, **kwargs):
    pprint(*args, stream=sys.stderr, **kwargs)
