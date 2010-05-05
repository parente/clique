'''
Defines constants representing keys and modifiers and their mappings to
commands.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
# modifier constants
MOD_NONE = 0
MOD_SHIFT = 1
MOD_CTRL = 2
MOD_ALT = 4
MOD_KP_SHIFT = 8

# keyboard message tuples containing virtual keycode and extended key flag
UNDEFINED = (0,0)
L_ALT = (164, 0)
R_ALT = (165, 1)
L_CTRL = (162, 0)
R_CTRL = (163, 0)
#L_APPS
R_APPS = (93, 1)
L_WIN = (91, 1)
R_WIN = (92, 1)
F1 = (112, 0)
F2 = (113, 0)
F3 = (114, 0)
F4 = (115, 0)
F5 = (116, 0)
F6 = (117, 0)
F7 = (118, 0)
F8 = (119, 0)
F9 = (120, 0)
F10 = (121, 0)
F11 = (122, 0)
F12 = (123, 0)
ESCAPE = (27,0)
TAB = (9,0)
HOME = (36,1)
END = (35,1)
PAGEUP = (33,1)
PAGEDOWN = (33,1)
INSERT = (45,1)
LEFT = (37,1)
RIGHT = (39,1)
UP = (38,1)
DOWN = (40,1)
KP_0 = (96,0)
KP_1 = (97,0)
KP_2 = (98,0)
KP_3 = (99,0)
KP_4 = (100,0)
KP_5 = (101,0)
KP_6 = (102,0)
KP_7 = (103,0)
KP_8 = (104,0)
KP_9 = (105,0)
KP_MULTIPLY = (106, 0)
KP_SUBTRACT = (109, 0)
KP_HOME = (36, 0)
KP_DIVIDE = (111, 1)
KP_UP = (38, 0)
KP_PAGEUP = (33, 0)
KP_ADD = (107, 0)
KP_LEFT = (37, 0)
KP_CENTER = (12, 0)
KP_RIGHT = (39, 0)
KP_END = (35, 0)
KP_DOWN = (40, 0)
KP_PAGEDOWN = (34, 0)
KP_ENTER = (13, 1)
KP_ZERO = (96,0)
KP_PERIOD = (110,0)
KP_INSERT = (45, 0)
KP_DELETE = (46, 0)
KP_CLEAR = (12, 0)
DELETE = (46,1)
BACKSPACE = (8,0)
ENTER = (13,0)
L_SHIFT = (160, 0)
R_SHIFT = (161, 1)
CAPS_LOCK = (20, 0)
NUM_LOCK = (144, 0)

# internal input messages
SYS_INFORM_STARTUP = (-1, -1)
SYS_STARTUP = (-2, -1)

# mapping from message to name of method that will handle it
cmd_dispatch = {KP_SUBTRACT : 'OnChooseProgram',
                KP_MULTIPLY : 'OnChooseTask',
                KP_DIVIDE : 'OnChooseMemory',
                R_ALT : 'OnSearch',
                L_ALT : 'OnSearch',
                KP_ADD : 'OnRemember',
                KP_UP : 'OnHigh',
                KP_8 : 'OnHigh',
                UP : 'OnHigh',
                KP_DOWN : 'OnLow',
                KP_2 : 'OnLow',
                DOWN : 'OnLow',
                KP_ENTER : 'OnDoThat',
                KP_PERIOD : 'OnRead',
                KP_DELETE : 'OnRead',
                ESCAPE : 'OnEscape',
                TAB : 'OnNextSubTask',
                KP_CLEAR: 'OnMoreInfo',
                KP_5: 'OnMoreInfo',
                KP_7: 'OnPrevHigh',
                KP_HOME: 'OnPrevHigh',
                KP_9: 'OnNextHigh',
                KP_PAGEUP: 'OnNextHigh',
                KP_LEFT : 'OnPrevMid',
                KP_4 : 'OnPrevMid',
                LEFT : 'OnPrevMid',
                KP_RIGHT : 'OnNextMid',
                KP_6 : 'OnNextMid',
                RIGHT : 'OnNextMid',
                KP_PAGEDOWN : 'OnNextLow',
                KP_3 : 'OnNextLow',
                KP_END : 'OnPrevLow',
                KP_1 : 'OnPrevLow',
                KP_INSERT : 'OnShutUp',
                KP_0 : 'OnShutUp',
                DELETE : 'OnDelete',
                BACKSPACE : 'OnBackspace',
                ENTER: 'OnEnter',
                SYS_INFORM_STARTUP: 'OnInformSystemStartup',
                SYS_STARTUP: 'OnSystemStartup'}

SEARCH_MOD = MOD_ALT

# mapping from message with shift held to method that will handle it
modified_cmd_dispatch = {(MOD_SHIFT, TAB): 'OnPrevSubTask',
                         (MOD_KP_SHIFT, KP_9): 'OnIncRate',
                         (MOD_KP_SHIFT, KP_PAGEUP): 'OnIncRate',
                         (MOD_KP_SHIFT, KP_PAGEDOWN): 'OnDecRate',
                         (MOD_KP_SHIFT, KP_3): 'OnDecRate',
                         (MOD_KP_SHIFT, KP_7): 'OnIncVolume',
                         (MOD_KP_SHIFT, KP_HOME): 'OnIncVolume',
                         (MOD_KP_SHIFT, KP_END): 'OnDecVolume',
                         (MOD_KP_SHIFT, KP_1): 'OnDecVolume',
                         (MOD_KP_SHIFT, KP_5) : 'OnWhereAmI',
                         (MOD_KP_SHIFT, KP_CENTER) : 'OnWhereAmI',
                         (MOD_KP_SHIFT, KP_4) : 'OnReplayHistory',
                         (MOD_KP_SHIFT, KP_LEFT) : 'OnReplayHistory',
                         (MOD_SHIFT|MOD_KP_SHIFT, ESCAPE) : 'OnInformSystemShutdown',
#                         (MOD_KP_SHIFT, KP_ENTER) : 'OnImDone',
                         (MOD_ALT, KP_LEFT) : 'OnPrevSearch',
                         (MOD_ALT, KP_4) : 'OnPrevSearch',
                         (MOD_ALT, LEFT) : 'OnPrevSearch',
                         (MOD_ALT, KP_RIGHT) : 'OnNextSearch',
                         (MOD_ALT, KP_6) : 'OnNextSearch',
                         (MOD_ALT, RIGHT) : 'OnNextSearch',
                         (MOD_ALT, BACKSPACE) : 'OnBackspaceSearch',
                         (MOD_CTRL, RIGHT) : 'OnNextMidMod',
                         (MOD_CTRL, LEFT) : 'OnPrevMidMod',
                         (MOD_CTRL, KP_RIGHT) : 'OnNextMidMod',
                         (MOD_CTRL, KP_LEFT) : 'OnPrevMidMod',
                         (MOD_CTRL, KP_6) : 'OnNextMidMod',
                         (MOD_CTRL, KP_4) : 'OnPrevMidMod'}

# add support for registering mappings from outside this package
cmd_id = [-1000, -1]
def GenCommandID():
  '''
  Generates a unique command ID for internal messaging.

  @return: Unique ID for use in a L{Input.Messages.InboundMessage}
  @rtype: 2-tuple of integer
  '''
  rv = tuple(cmd_id)
  cmd_id[0] += 1
  return rv

def AddDispatch(cmd_dict):
  '''
  Update the command dispatch to include the provided key/method name pairs.

  @param cmd_dict: Key/method name pairs
  @type cmd_dict: dictionary
  '''
  cmd_dispatch.update(cmd_dict)

def AddModifiedDispatch(cmd_dict):
  '''
  Update the modified command dispatch to include the provided key/method name
  pairs.

  @param cmd_dict: Key/method name pairs
  @type cmd_dict: dictionary
  '''
  modified_cmd_dispatch.update(cmd_dict)
