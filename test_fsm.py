import unittest

import poxfsm as pm


GO = ord('g')
HALT = ord('h')
LISTEN = ord('L')


def find_event(events, code, data=None):
    result = False
    for each in events:
        if each.code == code:
            if data is not None:
                if each.data == data:
                    result = True
                    break
            else:
                result = True
                break
    return result


class TestFSM(unittest.TestCase):

    def test_fsm1(self):
        # GO from idle to inhibit, (halt) IDLE [XOFF]
        cvsm = pm.SMLoop()
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_IDLE)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_INH)

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, HALT))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_IDLE)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XOFF))

    def test_fsm2(self):
        # idle to inhibit to norm, norm, norm, (halt) IDLE [XOFF]
        cvsm = pm.SMLoop()

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_CVOK))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_CVOK))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, HALT))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_IDLE)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XOFF))

    def test_fsm3(self):
        # idle to inhibit, norm, warn, norm, warn, (halt) IDLE [XOFF]
        cvsm = pm.SMLoop()

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_WARN)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_CVOK))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_WARN)

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, HALT))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_IDLE)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XOFF))

    def test_fsm4(self):
        # idle to inhibit, norm, warn, act [XON], (halt) IDLE [XOFF]
        cvsm = pm.SMLoop()

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_ACT)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XON))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, HALT))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_IDLE)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XOFF))

    def test_fsm5(self):
        # idle, inh, norm, warn, act [XON], (timer) norm [XOFF]
        cvsm = pm.SMLoop()

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_ACT)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XON))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XOFF))

    def test_fsm6(self):
        # idle, inh, norm, (rec fail) act [XON], (timer) norm [XOFF]
        cvsm = pm.SMLoop()

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_SRFAIL))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_ACT)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XON))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XOFF))

    def test_fsm7(self):
        # idle, inh, norm, warn, (rec fail) act [XON], (timer) norm [XOFF]
        cvsm = pm.SMLoop()

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_WARN)

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_SRFAIL))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_ACT)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XON))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_XOFF))

    # phrase state machine (psm) interaction

    def test_fsm100(self):
        # idle, inh, norm, activate psm, (halt), psm idle
        cvsm = pm.SMLoop()
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, LISTEN))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, HALT))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_IDLE)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_IDLE)

    def test_fsm101(self):
        # idle, inh, norm, warn, activate psm, (halt), psm idle
        cvsm = pm.SMLoop()
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, LISTEN))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_WARN)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, HALT))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_IDLE)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_IDLE)

    def test_fsm120(self):
        # idle, inh, norm, cycle speech recognition loop (True/False)
        cvsm = pm.SMLoop()
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, LISTEN))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_SR))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_SPK)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_SAY_REP))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_SDONE))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_REC)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_SRGO))

        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_RDONE, True))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)
        self.assertTrue(find_event(outputs, pm.SMEvent.E_SRACK, 0))

        # loop again but with False result (one strike)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_SR))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_SDONE))
        outputs = cvsm.crank(pm.SMEvent(pm.SMEvent.E_RDONE, False))
        self.assertTrue(find_event(outputs, pm.SMEvent.E_SRACK, 1))

    def test_fsm121(self):
        # idle, inh, norm (psm start), act (psm stop), norm (psm go)
        cvsm = pm.SMLoop()
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, LISTEN))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_ACT)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_STOP)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)

    def test_fsm122(self):
        # idle, inh, norm, psm times out waiting for speech completion
        cvsm = pm.SMLoop()
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, LISTEN))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_SR))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_SPK)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_SR))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)

    def test_fsm123(self):
        # idle, inh, norm, psm times out waiting for speech recognition done
        cvsm = pm.SMLoop()
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, GO))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_CV))
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_KEY, LISTEN))
        self.assertEqual(cvsm.state, pm.SMLoop.STATE_NORM)
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)

        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_SR))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_SPK)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_SDONE))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_REC)
        cvsm.crank(pm.SMEvent(pm.SMEvent.E_TMR_SR))
        self.assertEqual(cvsm.psm.state, pm.SMPhrase.STATE_WAIT)


if __name__ == '__main__':
    unittest.main()
