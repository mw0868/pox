import unittest

import poxcom as pc


class TestFSM(unittest.TestCase):

    def test_fsm1(self):
        # idle, bad address, still idle
        rxsm = pc.RXFSM()
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        result = rxsm.crank(7)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        self.assertTrue(result is None)

    def test_fsm2(self):
        # idle, good addr, size=1, one bytes, cmd generated (no data)
        rxsm = pc.RXFSM()
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        result = rxsm.crank(2)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_ADDR)
        self.assertTrue(result is None)
        result = rxsm.crank(1)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_SIZE)
        self.assertTrue(result is None)
        result = rxsm.crank(24)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        self.assertTrue(result is not None)
        self.assertEqual(result.cmd_id, 24)
        self.assertTrue(result.data is None)

    def test_fsm3(self):
        # idle, good addr, size=2, two bytes, cmd generated
        rxsm = pc.RXFSM()
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        result = rxsm.crank(2)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_ADDR)
        self.assertTrue(result is None)
        result = rxsm.crank(2)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_SIZE)
        self.assertTrue(result is None)
        result = rxsm.crank(0)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_DATA)
        self.assertTrue(result is None)
        result = rxsm.crank(0)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        self.assertTrue(result is not None)
        self.assertEqual(result.cmd_id, 0)
        self.assertEqual(result.data, bytearray('\x00'))

    def test_fsm4(self):
        # idle, good address, bad size, idle
        rxsm = pc.RXFSM()
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        result = rxsm.crank(2)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_ADDR)
        self.assertTrue(result is None)
        result = rxsm.crank(0)  # too small
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        self.assertTrue(result is None)
        result = rxsm.crank(2)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_ADDR)
        self.assertTrue(result is None)
        result = rxsm.crank(9)  # too big
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        self.assertTrue(result is None)

    def test_fsm5(self):
        # idle, good address, good size, invalid first data byte
        rxsm = pc.RXFSM()
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        result = rxsm.crank(2)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_ADDR)
        self.assertTrue(result is None)
        result = rxsm.crank(2)
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_SIZE)
        self.assertTrue(result is None)
        result = rxsm.crank(99)  # illegal
        self.assertEqual(rxsm.state, pc.RXFSM.STATE_IDLE)
        self.assertTrue(result is None)

    def test_pox100(self):
        import time
        import Queue
        com = pc.Com()
        port = "/dev/cu.USA19H142P1.1"
        self.assertTrue(com.open(port, 9600))

        # run com loop for a few seconds
        # - code checks for external device reset
        # - visual check for "heartbeat"
        q = Queue.Queue()
        com.start(q)
        k = 0
        result = None
        while k < 40:
            while not q.empty():
                result = q.get()
                q.task_done()
            time.sleep(0.1)
            k += 1
            if k == 25:
                com.post_cmd("rst", "")
        self.assertEqual(result, "COM rst")


if __name__ == '__main__':
    unittest.main()
