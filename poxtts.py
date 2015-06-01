# poxtts.py

"""POX Text-to-Speech stuff

The TTSDaemon class is a daemon for issuing text-to-speech commands.
On Mac OS X, it uses a system call to the built-in "say" routine to perform
text-to-speech operations.  Mac systems preferences can be changed to alter
the speech qualities.  Windows can use pyttsx.

Commands and responses are strings.  The thread owner must have a Queue
and pass it to TTSDaemon at initialization.  The TTSDaemon waits
for commands to be placed in its own Queue.

Input Commands:
    say <string>
    - Tells process to say the phrase in the string.

Output Responses:
    TTS done
    - Speaking of phrase has completed.

"""

import os
import sys
import threading
import Queue


POX_TTS = "TTS"


def speak(text):
    if sys.platform == 'darwin':
        # for Mac (darwin) use system call with built in 'say' command
        # which needs double quotes around incoming string
        # otherwise contractions won't work
        os.system('say "' + text + '"')
    else:
        # for Windows, try using pyttsx
        # unfortunately that module seems to have problems on a Mac
        pass


def handle_tts_command(cmd):
    stokens = cmd.split()
    if len(stokens) >= 2:
        # requires at least two tokens:  <cmd> <data>
        cmd_id = stokens[0]
        if cmd_id == "say":
            text = " ".join(stokens[1:])
            speak(text)
    return stokens


class TTSDaemon(object):

    def __init__(self):
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
        :param cmd: command string ("say")
        :param data: data string (text to be spoken)
        """
        if self._cmd_thread.is_alive():
            s = "{0} {1}".format(cmd, data)
            self._cmd_rx_queue.put(s)

    def _thread_function(self):
        """
        Implements daemon loop.
        - Checks for command
        - Begins speech
        - Let's App know when speech is done
        """
        while True:
            item = self._cmd_rx_queue.get()
            self._cmd_rx_queue.task_done()
            handle_tts_command(item)
            if self._cmd_tx_queue is not None:
                # let main app know speaking of phrase is done
                s = "{0} {1}".format(POX_TTS, "done")
                self._cmd_tx_queue.put(s)
