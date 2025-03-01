import os
import pprint
import tempfile

DEFAULT_LOG_FILE = "%s/%s" % (tempfile.gettempdir(), "lwe-debug.log")
LOG_FILE = os.environ.get("LWE_DEBUG_LOG_FILE", DEFAULT_LOG_FILE)

pp = pprint.PrettyPrinter()
pf = pprint.PrettyPrinter(stream=open(LOG_FILE, "w"))


def console(*args, **kwargs):
    pp.pprint(*args, **kwargs)


def file(*args, **kwargs):
    pf.pprint(*args, **kwargs)
