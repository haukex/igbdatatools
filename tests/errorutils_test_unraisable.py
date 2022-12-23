#!/usr/bin/env python3

# WARNING: Line numbers in this file are hard-coded in test_errorutils.py!

def testfunc():  # pragma: no cover
    raise RuntimeError("Bar")

class Foo:
    def __del__(self):  # pragma: no cover
        testfunc()

if __name__ == '__main__':  # pragma: no cover
    import errorutils
    import gc
    # only set up our custom handlers when we're run, not loaded as a module!
    errorutils.init_handlers()
    foo = Foo()
    foo = None
    gc.collect()
