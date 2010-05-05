'''
Defines convenience constants for pyAA.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import pyAA

SELECTED = pyAA.Constants.STATE_SYSTEM_SELECTED
FOCUSED = pyAA.Constants.STATE_SYSTEM_FOCUSED
COLLAPSED = pyAA.Constants.STATE_SYSTEM_COLLAPSED
EXPANDED = pyAA.Constants.STATE_SYSTEM_COLLAPSED
INVISIBLE = pyAA.Constants.STATE_SYSTEM_INVISIBLE
SELECT_AND_FOCUS = pyAA.Constants.SELFLAG_TAKEFOCUS|pyAA.Constants.SELFLAG_TAKESELECTION
FOCUS = pyAA.Constants.SELFLAG_TAKEFOCUS
SELECT = pyAA.Constants.SELFLAG_TAKESELECTION
EXTEND_SELECT = pyAA.Constants.SELFLAG_EXTENDSELECTION
UP = pyAA.Constants.NAVDIR_UP
DOWN = pyAA.Constants.NAVDIR_DOWN
LEFT = pyAA.Constants.NAVDIR_LEFT
RIGHT = pyAA.Constants.NAVDIR_RIGHT
FIRST = pyAA.Constants.NAVDIR_FIRSTCHILD
LAST = pyAA.Constants.NAVDIR_LASTCHILD
PREVIOUS = pyAA.Constants.NAVDIR_PREVIOUS
NEXT = pyAA.Constants.NAVDIR_NEXT
