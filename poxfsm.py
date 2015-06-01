# poxfsm.py

"""POX Finite State Machine stuff
- SMEvent class and codes
- SMPhrase class for Listen-and-Repeat state machine
- SMLoop class for main face recognition state machine

"""

import poxutil as pu


MAX_LEVEL = 10  # goes up with number of misses (does nothing else yet)

KEY_GO = ord('g')
KEY_HALT = ord('h')
KEY_LISTEN = ord('L')

USER_KEYS = [KEY_GO, KEY_HALT, KEY_LISTEN]


class SMEvent(object):
    # unique event codes
    E_NONE = 0x0
    E_KEY = 0x1  # key pressed
    E_TMR_CV = 0x2  # computer vision state machine timer expired
    E_CVOK = 0x3  # valid face/eye detection
    E_SRFAIL = 0x4  # speech recognition failure (based on strikes)
    E_TMR_SR = 0x5  # speech rec. state machine timer expired
    E_SRGO = 0x6  # speech recognition begin
    E_STOP = 0x7  # stop phrase machine
    E_GO = 0x8  # restart phrase machine
    E_SRACK = 0x9  # speech recognition result has been processed
    E_XON = 0x10  # external action begin
    E_XOFF = 0x11  # external action end
    E_SAY = 0x12  # say a phrase
    E_SAY_REP = 0x13  # say a canned phrase to be repeated
    E_SDONE = 0x20  # spoken phrase done
    E_RDONE = 0x21  # recognition done

    def __init__(self, code=E_NONE, data=None):
        self.code = code
        self.data = data


class SMPhrase(object):
    # states
    STATE_IDLE = 0
    STATE_WAIT = 1
    STATE_SPK = 2
    STATE_REC = 3
    STATE_STOP = 4

    # timer settings
    WAIT_TIMEOUT_SEC = 10  # interval between end of rec and start of spk
    REC_TIMEOUT_SEC = 25  # at least 10sec longer than poxrec.py timeout
    SPK_TIMEOUT_SEC = 10  # should be longer than longest phrase

    def __init__(self):
        self.state = SMPhrase.STATE_IDLE
        self.timer = pu.PolledTimer()
        self.strikes = 0
        self.snapshot = {"color": "black"}

    def _to_wait(self):
        # helper for transition to wait state (no outputs generated)
        self.timer.start(SMPhrase.WAIT_TIMEOUT_SEC)
        self.state = SMPhrase.STATE_WAIT

    def crank(self, this_event):
        assert (isinstance(this_event, SMEvent))

        state_outputs = []

        # CHECK FOR HIGH-PRIORITY STOP
        # if in any state other than idle and STOP occurs
        # - reset strikes
        # - stop timer
        # - enter STOP state
        if self.state != SMPhrase.STATE_IDLE:
            if this_event.code == SMEvent.E_STOP:
                self.strikes = 0
                self.timer.stop()
                self.state = SMPhrase.STATE_STOP
                # *** EARLY EXIT ***
                return state_outputs

        if self.state == SMPhrase.STATE_IDLE:
            # if key LISTEN then TO WAIT
            if this_event.code == SMEvent.E_KEY:
                if this_event.data == KEY_LISTEN:
                    self._to_wait()
                    # ANNOUNCE START OF SPEECH MODE
                    self.snapshot["color"] = "brick"
                    state_outputs.append(SMEvent(SMEvent.E_SAY,
                                                 "listen and repeat"))
        elif self.state == SMPhrase.STATE_WAIT:
            if this_event.code == SMEvent.E_TMR_SR:
                self.timer.start(SMPhrase.SPK_TIMEOUT_SEC)
                self.state = SMPhrase.STATE_SPK
                # command phrase to be spoken
                state_outputs.append(SMEvent(SMEvent.E_SAY_REP))
        elif self.state == SMPhrase.STATE_SPK:
            if this_event.code == SMEvent.E_TMR_SR:
                # likely due to TTS process not started
                self._to_wait()
            elif this_event.code == SMEvent.E_SDONE:
                self.timer.start(SMPhrase.REC_TIMEOUT_SEC)
                self.state = SMPhrase.STATE_REC
                # COMMAND START OF RECOGNITION
                state_outputs.append(SMEvent(SMEvent.E_SRGO))
        elif self.state == SMPhrase.STATE_REC:
            if this_event.code == SMEvent.E_TMR_SR:
                # likely due to REC process not started (or hung)
                self._to_wait()
            elif this_event.code == SMEvent.E_RDONE:
                self._to_wait()
                # GOT A RESULT SO UPDATE STRIKE COUNT
                # THEN ACK RESULT WITH THE NUMBER OF STRIKES
                ack_strikes = 0
                if not this_event.data:
                    self.strikes += 1
                    ack_strikes = self.strikes
                else:
                    self.strikes = 0
                srack_event = SMEvent(SMEvent.E_SRACK, ack_strikes)
                state_outputs.append(srack_event)
        elif self.state == SMPhrase.STATE_STOP:
            if this_event.code == SMEvent.E_GO:
                self._to_wait()

        return state_outputs


class SMLoop(object):
    # states
    STATE_IDLE = 0  # stopped
    STATE_INH = 1  # start-up delay
    STATE_NORM = 2  # valid face/eye detections
    STATE_WARN = 3  # string of misses, warning to user
    STATE_ACT = 4  # act after too many misses

    # timer settings
    INH_TIMEOUT_SEC = 5  # delay before starting
    NORM_TIMEOUT_SEC = 4  # no face/eye in this time, goes to WARN
    WARN_TIMEOUT_SEC = 3  # no face/eye in this time, goes to ACT
    ACT_TIMEOUT_SEC = 5  # duration of ACT

    def __init__(self):
        self.state = SMLoop.STATE_IDLE
        self.cv_timer = pu.PolledTimer()
        self.psm = SMPhrase()
        self.level = 0
        self.snapshot = {"color": "black",
                         "label": "IDLE",
                         "prog": "0"}

    def is_idle(self):
        return self.state == SMLoop.STATE_IDLE

    def _to_norm(self):
        # helper for transition to norm state (no outputs generated)
        self.cv_timer.start(SMLoop.NORM_TIMEOUT_SEC)
        self.state = SMLoop.STATE_NORM

    def _to_act(self, temp_outputs):
        # helper for transition to ACT state
        self.cv_timer.start(SMLoop.ACT_TIMEOUT_SEC)
        self.state = SMLoop.STATE_ACT
        # INCREASE LEVEL UP TO ITS MAXIMUM
        # STOP PHRASE MACHINE
        # TURN ON EXTERNAL ACTION (PASS ALONG NEW LEVEL DATA)
        if self.level < MAX_LEVEL:
            self.level += 1
        temp_outputs.extend(self.psm.crank(SMEvent(SMEvent.E_STOP)))
        temp_outputs.append(SMEvent(SMEvent.E_XON, self.level))

    def check_timers(self):

        # first update snapshot that is used for display
        # because it has some timer-based stuff

        # get data for progress bar for speech recognition
        if self.psm.state == SMPhrase.STATE_REC:
            self.snapshot["prog"] = str(self.psm.timer.sec())
        else:
            self.snapshot["prog"] = "0"

        # get data for status indicator
        if self.state == SMLoop.STATE_IDLE:
            self.snapshot["color"] = "black"
            self.snapshot["label"] = "IDLE"
        elif self.state == SMLoop.STATE_INH:
            self.snapshot["color"] = "blue"
            self.snapshot["label"] = str(self.cv_timer.sec())
        elif self.state == SMLoop.STATE_NORM:
            self.snapshot["color"] = "green"
            self.snapshot["label"] = "OK"
        elif self.state == SMLoop.STATE_WARN:
            self.snapshot["color"] = "yellow"
            self.snapshot["label"] = str(self.cv_timer.sec())
        elif self.state == SMLoop.STATE_ACT:
            self.snapshot["color"] = "red"
            self.snapshot["label"] = "FAIL"

        tmr_outputs = []

        # handle own timeouts first
        flag, t = self.cv_timer.update()
        if flag:
            tmr_outputs.append(SMEvent(SMEvent.E_TMR_CV))

        # then those of sub-machine for phrase control
        flag, t = self.psm.timer.update()
        if flag:
            tmr_outputs.append(SMEvent(SMEvent.E_TMR_SR))

        return tmr_outputs

    def crank(self, this_event):
        assert (isinstance(this_event, SMEvent))

        state_outputs = []

        # CHECK FOR HIGH-PRIORITY HALT
        # in any state other than idle and halt event occurs
        # - stop timer
        # - reset level
        # - go back to idle
        # - stop everything else related to monitoring
        if self.state != SMLoop.STATE_IDLE:
            if this_event.code == SMEvent.E_KEY:
                if this_event.data == KEY_HALT:
                    self.cv_timer.stop()
                    self.level = 0
                    self.state = SMLoop.STATE_IDLE
                    # NEW PHRASE STATE MACHINE (IDLE, MUST BE RESTARTED)
                    # TURN OFF ANY EXTERNAL ACTION
                    # ANNOUNCE HALT
                    self.psm = SMPhrase()
                    state_outputs.append(SMEvent(SMEvent.E_XOFF))
                    state_outputs.append(SMEvent(SMEvent.E_SAY,
                                                 "session halted"))
                    # EARLY EXIT
                    return state_outputs

        if self.state == SMLoop.STATE_IDLE:
            if this_event.code == SMEvent.E_KEY:
                if this_event.data == KEY_GO:
                    self.cv_timer.start(SMLoop.INH_TIMEOUT_SEC)
                    self.state = SMLoop.STATE_INH
                    # ANNOUNCE COUNTDOWN HAS STARTED
                    state_outputs.append(SMEvent(SMEvent.E_SAY,
                                                 "get ready"))
        elif self.state == SMLoop.STATE_INH:
            if this_event.code == SMEvent.E_TMR_CV:
                self._to_norm()
                # ANNOUNCE START OF MONITORING
                state_outputs.append(SMEvent(SMEvent.E_SAY,
                                             "go"))
        elif self.state == SMLoop.STATE_NORM:
            # in NORM pass event to phrase sub-machine
            state_outputs.extend(self.psm.crank(this_event))
            if this_event.code == SMEvent.E_CVOK:
                self._to_norm()
            elif this_event.code == SMEvent.E_TMR_CV:
                self.cv_timer.start(SMLoop.WARN_TIMEOUT_SEC)
                self.state = SMLoop.STATE_WARN
            elif this_event.code == SMEvent.E_SRFAIL:
                self._to_act(state_outputs)
        elif self.state == SMLoop.STATE_WARN:
            # in WARN pass event to phrase sub-machine
            state_outputs.extend(self.psm.crank(this_event))
            if this_event.code == SMEvent.E_CVOK:
                self._to_norm()
            elif this_event.code == SMEvent.E_TMR_CV:
                self._to_act(state_outputs)
            elif this_event.code == SMEvent.E_SRFAIL:
                self._to_act(state_outputs)
        elif self.state == SMLoop.STATE_ACT:
            if this_event.code == SMEvent.E_TMR_CV:
                self._to_norm()
                # RESTART PHRASE MACHINE
                # TURN OFF ANY EXTERNAL ACTION
                state_outputs.extend(self.psm.crank(SMEvent(SMEvent.E_GO)))
                state_outputs.append(SMEvent(SMEvent.E_XOFF))

        return state_outputs
