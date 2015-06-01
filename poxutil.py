"""POX Utility Classes
- PhraseManager Class
- PolledTimer Class

"""

import time
import random


class PolledTimer(object):
    """
    A PolledTimer object must have its update() method applied in a
    polling loop.  It's best to do this several times per second.
    """

    MIN_INTERVAL = 1
    MAX_INTERVAL = 3600

    def __init__(self):
        """
        Creates a timer in stopped state.
        """
        self._texp = 0
        self._sec = 0
        self._maxsec = 0

    def stop(self):
        """
        Puts timer into stopped state.
        """
        self._texp = 0
        self._sec = 0

    def sec(self):
        """
        Returns seconds remaining as of last update() call.
        :return: Seconds remaining.
        """
        return self._sec

    def start(self, t_exp):
        """
        Starts a timer.  Expiration time is relative to current system time.
        :param t_exp: Expiration time in seconds.
        """
        # apply allowed bounds on time interval
        # set expiration time in the future
        # set integer seconds remaining with input value
        checked_time = min(self.MAX_INTERVAL, max(t_exp, self.MIN_INTERVAL))
        self._texp = time.time() + checked_time
        self._sec = t_exp
        self._maxsec = t_exp

    def update(self):
        """
        Services the timer.  Call this routine in a polling loop.

        :return: (flag, time)
        flag - True if timer just expired, False otherwise
        time - Time remaining rounded up to nearest second
        """
        result = False
        if self._sec != 0:
            t = time.time()
            self._sec = int(self._texp - t) + 1
            if t > self._texp:
                # issue "one-shot" flag for expiration
                # clear data to disable timer
                self._texp = 0
                self._sec = 0
                result = True
        return result, self._sec


class PhraseManager(object):
    """
    Container class for strings (phrases) read from a file.
    In listen-and-repeat mode, the App will periodically say
    these phrases and wait for them to be repeated by a human.
    """

    def __init__(self):
        self._phrases = []
        self._next = -1

    def load(self, fname):
        result = False
        arr = []

        # try to read file
        try:
            with open(fname) as f:
                arr = f.readlines()
        except IOError:
            pass

        # clean up line endings and/or blank lines
        if len(arr):
            arr_clean = [x.rstrip().lstrip() for x in arr]
            self._phrases = [x for x in arr_clean if len(x)]

        # see if there is anything left
        if len(self._phrases):
            result = True
            self._next = 0
        return result

    def next_phrase(self, ransel=False):
        # if no phrases are loaded from file
        # then this will be the default phrase
        s = "this is a test"
        if len(self._phrases):
            # pick either a random phrase
            # or next in sequence (with rollover)
            if ransel:
                n = int(random.uniform(0, len(self._phrases)))
            else:
                n = self._next
                self._next = (self._next + 1) % len(self._phrases)
            s = self._phrases[n]
        return s
