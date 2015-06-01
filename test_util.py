
import unittest

import time
import poxutil as fu


class TestUtil(unittest.TestCase):

    def test_timer1_basic(self):
        # create a 1-second timer
        # update and see if it expires
        timer = fu.PolledTimer()
        timer.start(1)

        time.sleep(0.5)
        f, t = timer.update()
        self.assertEqual(f, False)
        self.assertEqual(t, 1)

        time.sleep(1)
        f, t = timer.update()
        self.assertEqual(f, True)
        self.assertEqual(t, 0)

    def test_timer2_restart(self):
        # create a 2-second timer
        # update twice then restart
        timer = fu.PolledTimer()
        timer.start(2)

        time.sleep(0.5)
        f, t = timer.update()
        self.assertEqual(f, False)
        self.assertEqual(t, 2)

        time.sleep(1)
        f, t = timer.update()
        self.assertEqual(f, False)
        self.assertEqual(t, 1)

        time.sleep(1)
        timer.start(2)
        self.assertEqual(timer.sec(), 2)

    def test_timer3_stop(self):
        # create a 30-second timer
        # do one update
        # stop the timer
        timer = fu.PolledTimer()
        timer.start(30)

        time.sleep(1.5)
        f, t, = timer.update()
        self.assertEqual(f, False)
        self.assertEqual(t, 29)

        timer.stop()
        self.assertEqual(timer.sec(), 0)

    def test_timer4_fast(self):
        # update 10 times per second
        # see if 1-sec timer expires after 10 updates
        timer = fu.PolledTimer()
        timer.start(1)

        ct = 0
        done = False
        while not done:
            # pad this a little to prevent any math weirdness
            time.sleep(0.105)
            ct += 1
            done, t = timer.update()
        self.assertEqual(ct, 10)

    def test_pm1(self):
        # see if we can handle non-existent file and get dummy phrase
        pm = fu.PhraseManager()
        self.assertFalse(pm.load("bogusname"))
        self.assertEqual(pm.next_phrase(), "this is a test")


if __name__ == '__main__':
    unittest.main()
