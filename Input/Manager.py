'''
Defines a manager for system wide keyboard input and a pipeline class
all classes must derive from in order to receive input messages.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import pyHook, Queue, time, thread, threading, pythoncom, win32api, win32con
import traceback, types
import System, Config
from Messages import KeyMessage, InboundMessage
from Constants import *

class Pipe(object):
  '''
  Segment of a pipeline for messages flowing into the system.

  @ivar focus: Next segment in the pipeline
  @type focus: L{Input.Manager.Pipe}
  @ivar ready: Is the object ready to handle input?
  @type ready: boolean
  @ivar has_focus: Is this object the focus of another object?
  @type has_focus: boolean
  '''
  def __init__(self):
    self.has_focus = False
    self.focus = None
    self.ready = True

  def IsReadyForInput(self, message):
    '''
    Checks if the object is ready to handle input. Allows system commands to
    leak through.

    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    @return: Is the object ready for input?
    @rtype: boolean
    '''
    if Config.debug: print self
    return self.ready or message.ID[0] < 0

  def ChangeFocus(self, new, message, auto_focus):
    '''
    Adopts a new L{Pipe} object as the observer. Informs the previous observer
    that it is no longer active.

    @param new: Object that will be adopted as the new observer
    @type new: L{Pipe}
    @param message: The input message that lead to this method call
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Is the new focus ready for interaction?
    @rtype: boolean
    @raise NotImplementedError: When passed something that cannot receive the 
        focus
    '''
    # just return false and deactivate if the new focus is None
    if new is None:
      old = self.focus
      self.focus = None
      ret = False
    else:
      # check if activation interface is supported
      try:
        mtd = new.OnActivate
      except AttributeError:
        raise NotImplementedError
      else:
        if isinstance(new, type):
          raise NotImplementedError
      # have to set new object to focus before activating
      old = self.focus
      self.focus = new
      # try to activate
      ret = mtd(message, auto_focus)
    # deactivate the old focus, no interface checks needed here, it was checked
    # when it received the focus
    if old is not None:
      old.OnDeactivate(message)
    return ret
    
  def FocusNow(self, new):
    '''
    Adopts a new observer immediately, without informing the previous observer
    or the new observer.

    @param new: Object that will be adopted as the new observer
    @type new: L{Pipe}
    '''
    self.focus = new

  def PropogateInput(self, message):
    '''
    Passes a message down the input pipeline until it reaches the deepest
    focused object. That object gets to handle the message first. If it does
    not, its parent does, etc. all the way back to the root.

    @param message: Input message to pass
    @type message: L{Input.Messages.InboundMessage}
    '''
    stop = False
    # peek at the message first before processing it
    #self.PreHandleInput(message)
    if self.focus:
      # let descendants handle the message first
      stop = self.focus.PropogateInput(message)
    if stop or not self.IsReadyForInput(message):
      return stop
    # handle the message ourselves
    return self.PostHandleInput(message)

  def PreHandleInput(self, message):
    '''
    Virtual method. Override to handle a message before propogating to 
    descendants.
    '''
    pass
    
  def PostHandleInput(self, message):
    '''
    Handles an input message by dispatching it to the appropriate method if
    it is implemented in this derived object.

    @param message: Input message to handle
    @type message: L{Input.Messages.InboundMessage}
    '''
    method = None
    # call a specific method if one exists for our key with modifiers held
    if message.Modified and \
       modified_cmd_dispatch.has_key((message.Modified, message.ID)):
      method_name = modified_cmd_dispatch[(message.Modified, message.ID)]
      try: method = getattr(self, method_name)
      except: pass
    # call a specific method if one exists for our key
    elif not message.Modified and cmd_dispatch.has_key(message.ID):
      method_name = cmd_dispatch[message.ID]
      try: method = getattr(self, method_name)
      except: pass
    elif message.Char:
      # unmodified characters or characters with shift held are plain text
      if not message.Modified or message.Modified == message.Shift:
        try: method = getattr(self, 'OnText')
        except: pass
      # characters with control held are searched
      elif message.Modified & SEARCH_MOD:
        try: method = getattr(self, 'OnTextSearch')
        except: pass
    # call the method to handle the message
    if method is not None:
      message.Stop = True
      method(message)
      message.Seen = True
      return message.Stop
    return False

  def OnActivate(self, message, auto_focus):
    '''
    Sets a flag that states if this object has the focus or not.

    @param message: Input message that caused this activation
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Is the control ready for interaction?
    @rtype: boolean
    '''
    self.has_focus = True
    return self.ready

  def OnDeactivate(self, message):
    '''
    Unsets a flag that state if this object has the focus or not.

    @param message: Input message that caused this deactivation
    @type message: L{Input.Messages.InboundMessage}
    '''
    self.has_focus = False

class Manager(threading.Thread, Pipe):
  '''
  Source of all input messages. Registers a global hook to capture system wide
  keyboard events. Stores all key events for later processing and prevents most
  from reaching applications directly. Implements the Singleton pattern.

  @ivar alive: Should we be watching for keyboard events and processing them?
  @type alive: boolean
  @ivar iput: Stores input events for later processing
  @type iput: Queue.Queue
  @ivar hm: Manages the system wide key hook
  @type hm: pyHook.HookMananger
  @ivar stateful: Keys with state that are monitored as pressed or not
  @type stateful: dictionary
  @ivar stateful_internal: Keys with monitored state not passed to the system
  @type stateful_internal: tuple
  @ivar LastEventTime: Time of last keyboard input
  @type LastEventTime: float
  @ivar tid: Thread ID of the message pump
  @type tid: integer
  '''
  instance = None

  def __new__(cls):
    '''
    Initializes a single instance of a class and stores it in a class variable.
    Returns that instance whenever this method is called again. Implements the
    Singleton design pattern.

    @return: Instance of this class
    @rtype: L{Manager}
    '''
    # return an existing instance
    if cls.instance is not None:
      return cls.instance

    # build and initialize a new instance
    self = threading.Thread.__new__(cls)
    threading.Thread.__init__(self)
    Pipe.__init__(self)

    self.LastEventTime = time.time()
    self.alive = True
    self.tid = None
    # create queue for input messages
    self.iput = Queue.Queue()
    # these keys are known as held or unheld
    self.stateful = {L_SHIFT: False, R_SHIFT: False,
                     L_ALT: False, R_ALT: False,
                     L_CTRL: False, R_CTRL: False,
                     KP_0: False, KP_INSERT: False,
                     KP_ADD: False, KP_ENTER: False}
    # these keys are stateful, but never reported to the OS
    self.stateful_internal = set((KP_0, KP_INSERT, KP_ADD, L_ALT, R_ALT,
                                 KP_ENTER, L_CTRL, R_CTRL))
    self.start()
    # store the instance for later
    cls.instance = self
    return self

  def __init__(self, *args, **kwargs): pass

  def run(self):
    '''Pump windows messages until death.'''
    # watch for key presses globally
    self.hm = pyHook.HookManager()
    self.hm.KeyDown = self.OnKeyDown
    self.hm.KeyUp = self.OnKeyUp
    if Config.hook_mouse:
      # get the mouse cursor out of the way
      win32api.SetCursorPos((0,0))
      # hook the mouse so all events are trapped
      self.hm.MouseAll = lambda x: False
      self.hm.HookMouse()
    self.hm.HookKeyboard()

    self.tid = thread.get_ident()
    pythoncom.PumpMessages()

  def OnKeyUp(self, event):
    '''
    Updates a dictionary with the state of stateful keys (e.g. Shift, Control,
    Alt, Keypad 0).

    @param event: Key event noticed
    @type event: pyHook.KeyboardEvent
    '''
    kid = (event.KeyID, event.Extended)
    if kid in (CAPS_LOCK, NUM_LOCK):
      # block modal keys
      return False
    elif event.Injected:
      if kid == L_SHIFT and self.stateful[L_SHIFT]:
        # block fake left shift release
        return False
    elif self.stateful.has_key(kid):
      # monitor keys that can be held down
      self.stateful[kid] = False
      if kid in self.stateful_internal:
        # send messages for some stateful keys too
        self.AddMessage(KeyMessage(event, MOD_NONE, False))
        # track the input message time
        self.LastEventTime = time.time()
        return False
    return True

  def OnKeyDown(self, event):
    '''
    Adds key events are added to a queue for later processing. Events are not
    handled now because this method is called in a separate by the OS and has
    fixed bounds on when it must return.

    @param event: Key event noticed
    @type event: pyHook.KeyboardEvent
    '''
    kid = (event.KeyID, event.Extended)
    # block caps lock and num lock (modal keys suck)
    if kid in (CAPS_LOCK, NUM_LOCK):
      return False
    # bail if the key was programmatically pressed (probably by us)
    elif event.Injected:
      return True
    elif self.stateful.has_key(kid):
      if kid in self.stateful_internal:
        if not self.stateful[kid]:
          # indicate the key is pressed
          self.stateful[kid] = True
          # send message for the start of a special stateful key press only
          self.AddMessage(KeyMessage(event, MOD_NONE, True))
          # track the input message time
          self.LastEventTime = time.time()
        return False
      else:
        # monitor keys that can be held down
        self.stateful[kid] = True
        return True
    else:
      # block and capture all others
      self.AddMessage(KeyMessage(event, self.GetModifiers(), True))
      # track the input message time
      self.LastEventTime = time.time()
      return False
    
  def GetModifiers(self):
    '''
    Computes the bitmask for all stateful modifier keys.
    
    @return: Modifier bitmask that can be passed to the constructor of 
        L{KeyMessage}
    @rtype: integer
    '''
    shift = (self.stateful[L_SHIFT]|self.stateful[R_SHIFT])*MOD_SHIFT
    alt = (self.stateful[L_ALT]|self.stateful[R_ALT])*MOD_ALT
    ctrl = (self.stateful[L_CTRL]|self.stateful[R_CTRL])*MOD_CTRL
    kps = (self.stateful[KP_0]|self.stateful[KP_INSERT])*MOD_KP_SHIFT
    return shift|alt|ctrl|kps

  def AddMessage(self, message):
    '''
    Adds a message to the queue for later processing.

    @param message: Event to queue
    @type message: L{Messages.InboundMessage}
    '''
    self.iput.put(message)

  def AddInformStartupMessage(self):
    '''Adds the message to play the introductory sound.'''
    self.iput.put(InboundMessage(SYS_INFORM_STARTUP))

  def AddStartupMessage(self):
    '''Adds the message to start interaction.'''
    self.iput.put(InboundMessage(SYS_STARTUP))

  def Destroy(self):
    '''
    Ceases message processing and returns false from the processing method.
    '''
    self.hm.UnhookMouse()
    self.hm.UnhookKeyboard()
    self.alive = False
    win32api.PostThreadMessage(self.tid, win32con.WM_QUIT, 0, 0)

  def ProcessMessages(self):
    '''
    Notifys observers about all of our queued messages. Messages are either
    passed to the direct descendent of the manager or routed directly to
    their intended destinations if specified.
    '''
    if not self.alive: return False
    # process input messages
    while 1:
      try:
        msg = self.iput.get_nowait()
      except Queue.Empty:
        break
      # route direct messages to their intended listeners
      if msg.Destination is not None:
        try:
          # let the listener handle the message without propogating it first
          msg.Destination.PostHandleInput(msg)
        except ReferenceError:
          # destination has died, just ignore
          pass
      elif msg.StartPipe is not None:
        msg.StartPipe.PropogateInput(msg)
      else:
        # default to routing through the manager
        self.PropogateInput(msg)
    return True

if __name__ == '__main__':
  import pythoncom
  m = Manager()
  pythoncom.PumpMessages()
