======
JSonic
======

:Author: Peter Parente
:Description: Clique: Perceptually based, task oriented auditory display for GUI applications
:Homepage: http://mindtrove.info/clique

Prerequisites
=============

Clique requires the following libraries:

* `pyAA`_
* `pyTTS`_
* `pySonic`_
* `pyHook`_
* `FMOD 3`_
* `PyProtocols`_
* `Python Win32 Extensions`_

The applications adapted for use with Clique are the following:

* `Day by Day Professional 2.0`_
* Microsoft Outlook Express on Windows XP
* Notepad on Windows XP
* `Winzip 10`_
* `Firefox 2`_

Caveats
=======

This is prototype code from my dissertation. It was written in 2005 and adapts the specific applications listed above for auditory display. The system relies on MSAA to drive the GUIs of those applications and various libraries that haven't been updated over the years. The code was only ever run and tested on Windows XP.

Don't expect it to run out of the box.

Instead, treat it as a reference implementation of the concepts discussed in my dissertation. Pilfer it for ideas, not lines of code. In fact, if I were to rewrite Clique today, I would keep the design of the auditory display the same but completely overhaul the internals.

License
=======

Copyright (c) 2008, Peter Parente
All rights reserved.

http://creativecommons.org/licenses/BSD/

.. _pyAA: http://sourceforge.net/projects/uncassist/files/
.. _pyTTS: http://sourceforge.net/projects/uncassist/files/
.. _pySonic: http://pysonic.sourceforge.net/
.. _pyHook: http://sourceforge.net/projects/uncassist/files/
.. _FMOD 3: http://www.fmod.org
.. _PyProtocols: http://peak.telecommunity.com/PyProtocols.html
.. _Python Win32 Extensions: http://starship.python.net/~skippy/win32/Downloads.html
.. _Day by Day Professional 2.0: http://www.blindsoftware.com/order_program.asp?id=16
.. _Winzip 10: http://www.winzip.com/index.htm
.. _Firefox 2: http://getfirefox.com