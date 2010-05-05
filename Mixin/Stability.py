'''
Defines a class that is notified whenever an event occurs in the process with
which it is associated.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import Mixer, pyAA, System
from View.Task import Container
import win32com.client, weakref, pythoncom, time, ctypes

SPIN_DELAY = 0.01 #0.01
SAFE_WAIT = 0.1 #0.5

# create an instance of WSH Shell
ws_shell = win32com.client.Dispatch("WScript.Shell")
# get a reference to the user32 DLL
user32 = ctypes.windll.user32

class StabilityMixin(Mixer.ClassMixer):
  '''
  Defines prefix and suffix methods that check-in with a stability manager and
  perturb it. Also defines an initialization method that establishes a reference
  to the proper stability manager instance. This class is used to add stability
  checks to pyAA.AccessibleObject.

  @ivar stable: Stability manager for the process that created this object
  @type stable: weakref.proxy for L{UIA.StabilityWatcher}
  '''
  def LeftClick(self):
    '''
    Performs a real left click on this AcccessibleObject. This method only
    exists to support broken applications that do not respond properly to the
    MSAA DoDefaultAction and Select methods and for some reason require a real
    mouse click to activate.
    '''
    l = self.Location
    # move to position
    user32.SetCursorPos(l[0]+1, l[1]+l[3]-1)
    # left down
    user32.mouse_event(0x8000|0x02, 0, 0, 0, None)
    # left up
    user32.mouse_event(0x8000|0x04, 0, 0, 0, None)

  def SendKeys(self, keys):
    '''
    Inject a key press into the input queue of the focused window.

    @param keys: Keys to press
    @type keys: string
    '''
    ws_shell.SendKeys(keys)

  def CheckStability(self):
    '''
    Checks the last time an event occurred in a process and compares it against
    a threshold. Blocks until the threshold has been passed.
    '''
    stab = self.GetStabilityWatcher()
    if stab is None: return
    while 1:
      # sleep and pump messages
      System.Sleep(SPIN_DELAY)
      # check if the interface is stable
      if (time.time() - stab.LastTime) > SAFE_WAIT:
        break
    stab.LastStable = time.time()

  def Disturb(self, name):
    '''Disturbs the last event time in the stability manager.'''
    stab = self.GetStabilityWatcher()
    if stab is None: return
    stab.Disturb()

  def GetStabilityWatcher(self):
    '''
    Locates the stability manager for this process by getting a reference to the
    singleton Container.Manager object and asking it for the program associated
    with the process ID of this object. The program is then queried for its
    stability watcher.

    @todo: stability should be a weakref; strong until process problem fixed
    '''
    try:
      return self.stable
    except AttributeError:
      pass
    # get the stability watcher for this object
    try:
      # get the process ID
      pid, tid = self.ProcessID
    except pyAA.Error:
      return None
    pm = Container.ProgramManager()
    self.stable = pm.GetStabilityWatcher(pid)
    return self.stable

  def CheckWrapper(self, name, prefix):
    '''
    Builds a method wrapper that checks with the stability manager before
    executing the original method.

    @param name: Original method name
    @type name: string
    @param prefix: Prefix used to rename the original method
    @type prefix: string
    @return: Method wrapping the original method
    @rtype: callable
    '''
    def Prototype(self, *args, **kwargs):
      self.CheckStability()
      return getattr(self, prefix+name)(*args, **kwargs)
    return Prototype

  def DisturbWrapper(self, name, prefix):
    '''
    Builds a method wrapper that disturbs the stability manager after executing
    the original method.

    @param name: Original method name
    @type name: string
    @param prefix: Prefix used to rename the original method
    @type prefix: string
    @return: Method wrapping the original method
    @rtype: callable
    '''
    def Prototype(self, *args, **kwargs):
      r = getattr(self, prefix+name)(*args, **kwargs)
      self.Disturb(name)
      return r
    return Prototype

  def InitializeWrapper(self, name, prefix):
    '''
    Builds a method wrapper that checks establihes a reference to the stability
    manager after executing the class constructor.

    @param name: Original method name
    @type name: string
    @param prefix: Prefix used to rename the original method
    @type prefix: string
    @return: Method wrapping the original method
    @rtype: callable
    '''
    def Prototype(self, *args, **kwargs):
      getattr(self, prefix+name)(*args, **kwargs)
      self.GetStabilityWatcher()
    return Prototype
