import pprint
import tempfile

LOG_FILE = '%s/%s' % (tempfile.gettempdir(), 'chatgpt-debug.log')

pp = pprint.PrettyPrinter()
pf = pprint.PrettyPrinter(stream=open(LOG_FILE, 'w'))

def console(*args, **kwargs):
    pp.pprint(*args, **kwargs)

def file(*args, **kwargs):
    pf.pprint(*args, **kwargs)
