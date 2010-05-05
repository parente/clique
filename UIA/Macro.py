'''
Defines the framework for user macros. Provides implementations for the most
common window open/close macros.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import EventManager
import pyAA, os, subprocess

def _testFeature(attr, target):
  '''
  Tests a the property value in attr with the one given in target to see if
  they are equal, first by a numeric integer comparison and then by a lowercase
  string comparison.

  @param attr: Any integer or string object to test
  @type attr: object
  @param target: Any integer or string value
  @type target: object
  '''
  # do a numeric comparison first
  try:
    return int(target) == int(attr)
  except ValueError:
    pass
  # do a straightforward comparison in lowercase
  try:
    return attr.lower().find(target.lower()) > -1
  except AttributeError:
    return False

def _onTest(event, ao, **features):
  '''
  Tests the properties of the given event and accessible object to see if they
  match those given in features.

  @param event: Accessible event to test
  @type event: L{pyAA.WinEvent}
  @param ao: Accessible object to test
  @type ao: L{pyAA.AccessibleObject}
  @param features: Name/value pairs representing the proprties to test and their
    target values
  @type features: dictionary
  '''
  for name, target in features.items():
    if target is None:
      # ignore blank targets
      continue
    try:
      # try to get the feature on the accessible first
      attr = getattr(ao, name)
      if not _testFeature(attr, target):
        return False
      else:
        continue
    except (AttributeError, pyAA.Error):
      pass
    try:
      # try to get the feature on the event next
      attr = getattr(event, name)
      if not _testFeature(attr, target):
        return False
    except (AttributeError, pyAA.Error):
      return False
  return True

class Macro(object):
  '''
  Schedules a number of actions to be performed on a GUI one after another.
  Handles cases where there is an indeterminate delay between one action and the
  next, like a window appearing before a key should be pressed. Support the
  yielding of control back to the thread that initiates the macro at various
  places in the macro.

  @ivar task: Task that started this macro
  @type task: L{View.Task.Base}
  @ivar result: Result of the last step in the sequence
  @type result: object
  @ivar name: Name of the case that advanced the macro to the next step
  @type name: string
  @ivar seq: Sequence of statements in the macro
  @type seq: generator
  @ivar finish: Result deferred until macro completion
  @type finish: pyAA.Defer.Deferred
  @ivar message: Message that caused the macro to start
  @type message: L{Input.Messages.InboundMessage}
  @ivar conditions: Conditions paired with flags indicating if they are one-shot
    or not
  @type conditions: dictionary
  @ivar _awaitingConditions: Conditions to set this object as a listener on the
    once the next step in the sequence completes
  '''
  def __init__(self, task=None, message=None, model=None, **kwargs):
    '''
    Initialize an instance.

    See instance variables for parameter descriptions.
    '''
    self.Initialize(task, message, model, kwargs)

  def __call__(self, task=None, message=None, model=None, **kwargs):
    '''
    Refreshes the macro parameters provided at instantiation time. Can be used
    to fill in params that were not available at instantiation time (e.g. a
    model).
    '''
    self.Initialize(task or self.task, message or self.message, 
                    model or self.model, kwargs)
    return self

  def Initialize(self, task, message, model, kwargs):
    '''
    Initializes instance variables.

    See instance variables for parameter definitions.
    '''
    self.__dict__.update(kwargs)
    self.task = task
    self.name = None
    self.seq = None
    self.model = model
    self.message = message
    self.result = model
    self.finish = pyAA.Defer.Deferred()
    self.conditions = {}
    self._awaitingConditions = []

  def Execute(self):
    '''
    Run the macro.

    @return: Deffered result
    @rtype: pyAA.Deferred
    '''
    self.seq = self.Sequence()
    self.Continue(self.model)
    return self.finish

  def Sequence(self):
    '''Virtual method. Yields immediately.'''
    yield True

  def _removeConditions(self, all):
    '''
    Removes registered conditions. All of them if all is True or only one-shot
    conditions if all is False.

    @param all: Remove all conditions (True) or just one-shot conditions
      (False)?
    @type all: boolean
    '''
    for cond, survive in self.conditions.items():
      if not survive or all:
        try:
          EventManager.removeCondition(cond)
          del self.conditions[cond]
        except ValueError:
          pass

  def _getPID(self):
    '''
    Gets the process ID of the L{model} object if one is available.

    @return: Process ID of the model object
    @rtype: integer
    '''
    try:
      # only register for events in this process if possible
      pid, tid = self.model.ProcessID
    except AttributeError:
      # register globally if not
      pid = None
    return pid

  def Continue(self, result=None, name=None):
    '''
    Continue to the next step in the sequence after the last yield.

    @param result: Result from the watcher that called this function
    @type result: object
    @param name: Name of the watcher that called this function
    @type name: string
    '''
    # do nothing if we get some errant call later
    if self.seq is None:
      return
    # remove one-shot conditions
    self._removeConditions(False)
    # hold onto the last result and name
    self.result = result or self.result
    self.name = name
    # perform the next step in the sequence
    if self.seq.next():
      # clean up all conditions
      self._removeConditions(True)
      # end the macro by making the callback
      self.seq = None
      self.finish.Callback(self.result, self.message)
    else:
      # set this object as a listener on all conditions
      for cond, name in self._awaitingConditions:
        cond.setListener(self.Continue, name)
      self._awaitingConditions = []

  def WatchForTimeout(self, timeout, name=None):
    '''
    Registers a future with the main message pump to be called at a later time
    indicating a timeout.

    @param timeout: Number of seconds to wait before timing out
    @type timeout: float
    '''
    System.Pump().RegisterFuture(timeout, self.Continue, name=name)

  def WatchForEvents(self, events, name=None, survive=False, **features):
    '''
    Watches for stated window events with the given features.

    @param events: List of events to watch
    @type events: list
    @param name: Name of the case where the window actually closes
    @type name: string
    @param survive: Does this watcher survive throughout the macro?
    @type survive: boolean
    @param features: Other features to monitor, given by their AA property name
    @type features: dictionary of string, regex, or callable
    '''
    pid = self._getPID()
    # register the features for all events
    for event in events:
      cond = EventManager.addCondition(event, _onTest, pid, **features)
      #cond.setListener(self.Continue, name)
      self._awaitingConditions.append((cond, name))
      self.conditions[cond] = survive

  def WatchForNewDialog(self, name=None, survive=False, ClassName='#32770',
                        **features):
    '''
    Watch for a new window to appear.

    @param name: Name of the case where the window actually appears
    @type name: string
    @param survive: Does this watcher survive throughout the macro?
    @type survive: boolean
    @param ClassName: Default dialog window class
    @type ClassName: string
    @param features: Features defining the desired event
    @type features: dictionary of string, regex, or callable
    '''
    kwargs = {}
    kwargs.update(features)
    kwargs['ClassName'] = ClassName
    self.WatchForEvents([pyAA.Constants.EVENT_SYSTEM_DIALOGSTART],
                        name, survive, **kwargs)

  def WatchForWindowClose(self, hwnd, name=None, survive=False):
    '''
    Watch for a window to close.

    @param hwnd: Handle of the window that should close
    @type hwnd: number
    @param name: Name of the case where the window actually closes
    @type name: string
    @param survive: Does this watcher survive throughout the macro?
    @type survive: boolean
    '''
    cond = EventManager.addCondition(pyAA.Constants.EVENT_OBJECT_DESTROY,
                                     _onTest, None, Window=hwnd)
    cond.setListener(self.Continue, name)
    self.conditions[cond] = survive

  def WatchForNewWindow(self, name=None, survive=False, **features):
    '''
    Watch for a new window to appear.

    @param name: Name of the case where the window actually appears
    @type name: string
    @param survive: Does this watcher survive throughout the macro?
    @type survive: boolean
    @param features: Features defining the desired event
    @type features: dictionary of string, regex, or callable
    '''
    self.WatchForEvents([pyAA.Constants.EVENT_SYSTEM_FOREGROUND,
                         pyAA.Constants.EVENT_OBJECT_SHOW],
                        name, survive, **features)

  def FindWindow(self, **features):
    '''
    Searches for a top level window that meets the given criteria.

    @param features: Features defining the desired event
    @type features: dictionary
    @return: Reference to the given window if found, else None
    @rtype: pyAA.AccessibleObject
    '''
    # create a watcher so we can use it's testing abilities
    w = pyAA.WindowWatcher()
    # get a ref to the desktop
    desktop = pyAA.AccessibleObjectFromDesktop(pyAA.Constants.OBJID_CLIENT)
    for c in desktop.Children:
      for key, test_val in features.items():
        # quit as soon as one attribute fails to match
        val = w.TestGeneral(c, key, test_val)
        if not val: break
      if val:
        # store the object as the result and return it
        self.result = c
        return c
    return None

  def CloseWindow(self):
    '''
    Closes the connected window by pressing its close button.
    '''
    b = self.result.ChildFromPath('/title bar[1]/push button[4]')
    b.DoDefaultAction()

  def RunFile(self, name):
    '''
    Run an executable.

    @param name: Filename of the program to run
    @type name: string
    '''
    try:
      os.startfile(name)
      return
    except Exception:
      pass
    try:
      subprocess.Popen(name)
    except Exception:
      pass

  def SendKeys(self, keys):
    '''
    Convenience method for sending keystroke from a macro. Keys are sent to the
    latest established model.

    @note: Selection here is critical; removing this line causes keystroke
      combos of length > 1 to fail and insert text instead
    @param keys: Keys to send formatted for the WSH SendKeys function
    @type keys: string
    '''
    self.result.Select(pyAA.Constants.SELFLAG_TAKEFOCUS)
    self.result.SendKeys(keys)

class StartWindowByKey(Macro):
  '''Convenience class. Presses keys and watches for a new window.'''
  Name = None
  ClassName = None
  def Sequence(self):
    # watch for a window
    self.WatchForNewWindow(ClassName=self.ClassName, Name=self.Name)
    # press some keys
    self.SendKeys(self.key_combo)
    yield False
    yield True

class EndWindowByKey(Macro):
  '''Convenience class. Presses Enter to end a dialog.'''
  Name = None
  ClassName = None
  key_combo = '{ENTER}'

  def Sequence(self):
    # watch for the window closing
    self.WatchForWindowClose(self.model.Window, 'done')
    # press the send button
    self.SendKeys(self.key_combo)
    yield False
    yield True

class HideWindowByKey(Macro):
  '''Convenience class. Presses Enter to hide a dialog.'''
  Name = None
  ClassName = None
  key_combo = '{ENTER}'

  def Sequence(self):
    # watch for the window closing
    self.WatchForEvents([pyAA.Constants.EVENT_OBJECT_HIDE], name='done',
                        Window=self.model.Window)
    # press the send button
    self.SendKeys(self.key_combo)
    yield False
    yield True

class StartWindowByButton(Macro):
  '''Convenience class. Presses a button and watches for a window.'''
  Name = None
  ClassName = None

  def Sequence(self):
    # watch for a window
    self.WatchForNewWindow(ClassName=self.ClassName, Name=self.Name)
    # press a button
    button = self.model.ChildFromPath(self.button_path)
    button.DoDefaultAction()
    yield False
    yield True

class EndWindowByButton(Macro):
  '''Convenience class. Presses the close button to close a window.'''
  Name = None
  ClassName = None
  button_path = '/title bar[1]/push button[4]'

  def Sequence(self):
    # watch for window closing
    self.WatchForWindowClose(self.model.Window, 'done')
    button = self.model.ChildFromPath(self.button_path)
    button.DoDefaultAction()
    yield False
    yield True

class WaitEndWindowByButton(EndWindowByButton):
  '''
  Convenience class. Waits for a number of external calls before completing by
  pressing a button.
  '''
  calls = 1
  def Sequence(self):
    for i in range(self.calls):
      yield False
    yield super(WaitEndWindowByButton, self).Sequence().next()
    yield True

class WaitEndWindowByKey(EndWindowByKey):
  calls = 1
  def Sequence(self):
    for i in range(self.calls):
      yield False
    yield super(WaitEndWindowByKey, self).Sequence().next()
    yield True

class DoNothing(Macro):
  '''Convenience class. Does nothing. Returns the model as the result.'''
  def Sequence(self):
    yield True

if __name__ == '__main__':
  m = Macro()
  o = m.FindWindow(Name='Day by Day for Pete', ClassName='ThunderRT6FormDC')
  print o.Name
