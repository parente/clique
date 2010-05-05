'''
Defines all output related objects and messages.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from Constants import ACTIVE_CTRL, ACTIVE_PROG, INACTIVE_PROG, CONTEXT, \
     NARRATOR, CONTENT, SUMMARY, CHANGE, LOOPING, AMBIENCE, \
     INTERMITTENT, TimeToSpeak
from Interface import ISound
from Messages import OutboundPacket as Packet
from Manager import Pipe, Manager
