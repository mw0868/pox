# pox
Python OpenCV Example

This project was an excuse to play with a variety of Python libraries.

I used Mac OS X and Python 2.7.6.  It has been tested with Mac OS X El Capitan:  10.11.2.

The application looks at a user's face and speaks phrases and listens for them to be repeated.
What's that good for?  I don't know.  But I learned a lot.  The app uses a bunch of libraries...

It uses Python OpenCV for face/eye recognition and a GUI window.
I used the following instructions.  Hopefully they'll work for you too.
http://www.jeffreythompson.org/blog/2013/08/22/update-installing-opencv-on-mac-mountain-lion/

It uses pyserial to send and receive commands through a serial port.
http://pyserial.sourceforge.net/

I attempted to use pyttsx to make the computer talk.  It seemed to have issues
on the Mac so I just used a "say" system call instead.  Here is the link anyway:
https://pypi.python.org/pypi/pyttsx/1.1

It uses SpeechRecognition to listen for phrases.  I never quite got all the
kinks out, but it does seem to work pretty well.  Here is the link:
https://pypi.python.org/pypi/SpeechRecognition/

You'll have to install a lot of other stuff to make that work.
