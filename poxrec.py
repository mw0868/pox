# poxrec.py

"""POX Speech Recognition Process

The RECDaemon class is a daemon for performing speech recognition.
It uses the following library:
https://pypi.python.org/pypi/SpeechRecognition/

It uses the Google API for speech recognition so the system must have
internet access.

Commands and responses are strings.  The thread owner must have a Queue
and pass it to RECDaemon at initialization.  The RECDaemon waits
for commands to be placed in its own Queue.

Input Commands:
    hear <string>
    - Tells process to listen for the phrase in the string.

Output Responses:
    REC <string>
    - String is "True" if phrase detected.
    - String is "False" if detection timed out.

"""

import threading
import Queue
import time

import speech_recognition as sr


POX_REC = "REC"
TIMEOUT = 12.0  # actual timeout may be 10 or more seconds long


class RecWrapper(object):

    def __init__(self):
        self.r = None
        self.ok = False

    def go(self):
        """
        Initializes speech recognition and performs self-test with WAV file.
        """
        # TODO -- get own Google API key
        self.r = sr.Recognizer()

        # self-test
        result = None
        audio = None
        try:
            with sr.WavFile('rec_test_phrase.wav') as source:
                audio = self.r.record(source)
        except IOError:
            result = "No wave file found"

        if audio is not None:
            try:
                s = self.r.recognize(audio)
                if s == "this is a test":
                    result = "Speech Recognition OK"
                    self.ok = True
            except IndexError:  # the API key didn't work
                result = "No internet connection"
            except KeyError:    # the API key didn't work
                result = "Invalid API key or quota maxed out"
            except LookupError:  # speech is unintelligible
                result = "Could not understand audio"
        return result

    def wait_for_phrase(self, timeout, phrase):
        result = False
        if self.ok:

            # perform timed grab of some audio
            audio = None
            with sr.Microphone() as source:
                try:
                    # this adjustment stuff seems to have hung once
                    # (maybe because of loud washing machine in background?)
                    # audio = self.r.adjust_for_ambient_noise(source)
                    audio = self.r.listen(source, timeout)
                except NameError:
                    # should throw TimeoutError according to docs
                    # but it is undefined so this will have to do
                    pass

            # then run recognizer (if we got some audio)
            if audio is not None:
                try:
                    ss = self.r.recognize(audio, show_all=True)
                    for each in ss:
                        if each['text'] == phrase:
                            result = True
                            break
                except LookupError:
                    pass

        return result


class RECDaemon(object):

    def __init__(self):
        self.srec = RecWrapper()
        self._cmd_rx_queue = Queue.Queue()
        self._cmd_tx_queue = None
        self._cmd_thread = None

    def start(self, cmd_tx_queue):
        """
        Starts daemon thread.
        :param cmd_tx_queue: App's event Queue
        """
        self._cmd_tx_queue = cmd_tx_queue
        self._cmd_thread = threading.Thread(target=self._thread_function)
        self._cmd_thread.setDaemon(True)
        self._cmd_thread.start()

    def post_cmd(self, cmd, data):
        """
        Enqueues command from main App.
        :param cmd: command string ("hear")
        :param data: data string (words to be recognized)
        """
        if self._cmd_thread.is_alive():
            s = "{0} {1}".format(cmd, data)
            self._cmd_rx_queue.put(s)

    def _handle_cmd(self, cmd):
        result = False
        stokens = cmd.split()
        if len(stokens) >= 2:
            # requires at least two tokens:  <cmd> <data>
            if stokens[0] == "hear":
                s = " ".join(stokens[1:])
                # subtracting some time makes sure next loop behaves
                tx = time.time() + TIMEOUT - 1.0
                while not result:
                    # if result comes before timeout
                    # but is false then try again
                    result = self.srec.wait_for_phrase(TIMEOUT, s)
                    if time.time() > tx:
                        break
        return result

    def _thread_function(self):
        """
        Implements initialization, self-test, and daemon loop.
        - Checks for command
        - Begins speech recognition
        - Let's App know when recognition is done and the result
        """

        # first do init and self-test
        result = self.srec.go()
        if self._cmd_tx_queue is not None:
            s = "{0} {1} {2}".format(POX_REC, "init", result)
            self._cmd_tx_queue.put(s)

        while True:
            item = self._cmd_rx_queue.get()
            self._cmd_rx_queue.task_done()
            result = self._handle_cmd(item)
            if self._cmd_tx_queue is not None:
                # let main app know recognition is done
                s = "{0} {1}".format(POX_REC, str(result))
                self._cmd_tx_queue.put(s)
