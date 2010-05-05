'''
Defines a global event manager that notifies observers when their registered
conditions are met.

@var _conditions: Dictionary with event types as keys and dictionaries as 
  values. Inner dictionaries are keyed by process IDs with L{Condition} objects
  as values.
@type _conditions: dictionary
@var _watchers: Dictionary of L{ConditionWatcher}s keyed by event type.
@type _watchers: dictionary

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import traceback, pyAA

_watchers = {}
_conditions = {}

class Condition(object):
  '''
  Stores data about a condition under which an observer should be notified.
  
  @ivar ProcessID: Process ID on which this condition is registered
  @type ProcessID: integer
  @ivar EventID: Event ID on which this condition is registered
  @type EventID: integer
  @ivar test_cb: Function to call to test the condition
  @type test_cb: callable
  @ivar notify_cbs: Function to call when the condition is satisfied and user
    data to pass to it
  @type notify_cbs: 2-tuple
  @ivar Remove: Should the condition be removed from consideration after it is
    satisfied once?
  @type Remove: boolean
  @ivar args: Positional arguments to provide to the test function
  @type args: list
  @ivar kwargs: Keyword arguments to provide to the test function
  @type kwargs: dictionary
  '''
  def __init__(self, pid, eid, test_cb, remove, args, kwargs):
    '''
    Stores the condition data.
    
    See instance variables for parameter descriptions.
    '''
    self.ProcessID = pid
    self.EventID = eid
    self.Remove = remove
    self.test_cb = test_cb
    self.notify_cb = None
    self.args = args
    self.kwargs = kwargs
    
  def __eq__(self, other):
    '''
    Compares this L{Condition} to another for equality of process ID, event ID,
    remove boolean, test callback, and all arguments to the test callback.
    
    @param other: Condition to compare
    @type other: L{Condition}
    '''
    return (self.ProcessID == other.ProcessID and
            self.EventID == other.EventID and 
            self.Remove == other.Remove and
            self.test_cb == other.test_cb and 
            self.args == other.args and
            self.kwargs == other.kwargs)
    
  def test(self, *args):
    '''
    Calls the test function.
    
    @param args: Objects to test
    @type args: list
    @return: Return value of the test
    @rtype: boolean
    '''
    return self.test_cb(*(args+self.args), **self.kwargs)
  
  def notify(self, *args):
    '''
    Calls the listener.
    
    @param args: Result data to provide to the listener
    @type args: list
    '''
    if self.notify_cb is not None:
      func, user_args = self.notify_cb
      func(*(args+user_args))
             
  def setListener(self, listener, *args):
    '''
    Sets the listener for notification.
    
    @param listener: Function to call when the condition is satisfied
    @type listener: callable
    @param args: User data to provide to the listener
    @type args: list
    '''
    self.notify_cb = (listener, args)

class ConditionCollection(object):
  '''
  Contains a list of conditions to be evaluated in order.
  
  @ivar conditions: List of conditions to check in order
  @type conditions: list
  @ivar pid: Process ID associated with this collection or None if global
  @type pid: integer
  '''
  def __init__(self, pid):
    '''
    Stores the process ID with which this collection is associated.
    
    @param pid: Process ID associated with this collection or None if global
    @type pid: integer
    '''
    self.pid = pid
    self.conditions = []
  
  def addCondition(self, condition, front=True):
    '''
    Adds a condition to the collection. Avoids adding conditions with the same
    values.
    
    @param condition: Condition to register
    @type condition: L{Condition}
    @param front: Add to the front of the collection to be considered first?
    @type front: boolean
    @see: Condition.__eq__
    '''
    try:
      self.conditions.index(condition)
      return
    except ValueError:
      pass
    if front:
      self.conditions.insert(0, condition)
    else:
      self.conditions.append(condition)
  
  def removeCondition(self, index=None, condition=None):
    '''
    Removes a condition from the collection.
    
    @param index: Index of the condition in the collection
    @type index: integer
    @param condition: Condition object to remove
    @type condition: L{Condition}
    @raise IndexError: When the given index is out of bounds
    @raise ValueError: When the given condition is not registered
    '''
    if index is not None:
      self.conditions.pop(index)
    elif condition is not None:
      self.conditions.remove(condition)
  
  def testConditions(self, event, ao):
    '''
    Tests if the given object passes any of the conditions. Removes a one-shot
    condition that is satisfied.
    
    @param event: Accessible event to test
    @type event: pyAA.WinEvent
    @param ao: Accessible object to test
    @type ao: pyAA.AccessibleObject
    @return: Condition that passed or None
    @rtype: L{Condition}
    '''
    for index, cond in enumerate(self.conditions):
      # check all process specific conditions
      try:
        rv = cond.test(event, ao)
      except Exception, e:
        # ignore all test exceptions and move on
        continue
      if rv:
        # notify and log all errors
        try:
          cond.notify(ao)
        except Exception:
          traceback.print_exc()
        if cond.Remove:
          # remove a one-shot condition
          self.removeCondition(index)
        return cond
    return None
  
class ConditionWatcher(pyAA.AAbase):
  '''
  Reference counted watcher object that releases itself when its reference count
  falls to zero.
  
  @ivar count: Current reference count
  @type count: integer
  '''
  def __init__(self):
    '''
    Initializes the reference count.
    '''
    super(ConditionWatcher, self).__init__()
    self.count = 0
    
  def ref(self):
    '''
    Increases the reference count by one.
    '''
    self.count += 1
  
  def unref(self):
    '''
    Decreases the reference count by one and releases this object if it falls
    to (or below) zero.
    '''
    self.count -= 1
    if self.count <= 0:
      self.Release()
      return True
    return False
    
def _onEvent(event):
  '''
  Checks if any of the register conditions are satisfied by the given event.
  Conditions associated with the process ID of the event are checked first
  followed by any global conditions.
  
  @param event: Accessible event
  @type event: pyAA.WinEvent
  '''
  # get conditions for the kind of event
  try:
    collections = _conditions[event.EventID]
  except KeyError:
    return
  
  # get the event source and its originating process
  ao = event.AccessibleObject
  try:
    pid, tid = ao.ProcessID
  except AttributeError:
    pass
  except pyAA.Error:
    return
  else:
    # get process specific conditions first
    try:
      collection = collections[pid]
    except KeyError:
      pass
    else:
      cond = collection.testConditions(event, ao)
      if cond is not None:
        if cond.Remove:
          # decrement the watcher reference count
          _unrefWatcher(event.EventID)
        return
    
  # try global conditions next
  try:
    collection = collections[None]
  except KeyError:
    pass
  else:
    cond = collection.testConditions(event, ao)
    if cond is not None:
      if cond.Remove:
        # decrement the watcher reference count
        _unrefWatcher(event.EventID)
  
def _refWatcher(event_id):
  '''
  Increments the reference count on a watcher for the given event type. Creates
  the watcher if it does not exist.
  
  @param event_id: Event type to monitor
  @type event_id: integer
  '''
  try:
    _watchers[event_id].ref()
  except KeyError:
    w = ConditionWatcher()
    w.AddWinEventHook(callback=_onEvent, event=event_id)
    w.ref()
    _watchers[event_id] = w

def _unrefWatcher(event_id):
  '''  
  Decrements the reference count on a watcher for the given event type. Removes
  it from the L{_watchers} dictionary if it not longer has any references.
  
  @param event_id: Event type to monitor
  @type event_id: integer
  '''
  if _watchers[event_id].unref():
    del _watchers[event_id]

def addCondition(eid, test_cb, pid=None, front=True, remove=False, *args, 
                 **kwargs):
  '''
  Adds a condition under which a notification should be generated for an event.
  Registers the condition under the given process ID if specified, or under
  the list of global conditions if not. Adds the condition to the front of the
  condition list if top is True, else to the end. Removes the condition when the
  first event satisfying it is encountered if remove is True, else leaves it.
  
  @param eid: Event which will trigger testing of the condition
  @type eid: integer
  @param test_cb: Function to call to test the event when it is received
  @type test_cb: callable
  @param pid: Process ID associated with this condition
  @type pid: integer
  @param front: Add the condition to the front of the list of conditions?
  @type front: boolean
  @param remove: Remove this condition after it has been satisfied once?
  @type remove: boolean
  @return: Condition that was registered
  @rtype: L{Condition}
  '''
  _refWatcher(eid)
  collections = _conditions.setdefault(eid, {})
  collection = collections.setdefault(pid, ConditionCollection(pid))
  cond = Condition(pid, eid, test_cb, remove, args, kwargs)
  collection.addCondition(cond, front)
  return cond

def removeCondition(condition):
  '''
  Removes a condition to prevent further notification.
  
  @param event_id: Event which will trigger testing of the condition
  @type event_id: integer
  @param condition: Condition to remove as returned by L{addCondition}
  @type condition: L{Condition}
  @param pid: Process ID associated with this condition
  @type pid: integer
  @raise KeyError: When the process ConditionCollection does not exist
  @raise ValueError: When the process Condition does not exist
  '''
  _unrefWatcher(condition.EventID)
  collections = _conditions[condition.EventID]
  collection = collections[condition.ProcessID]
  collection.removeCondition(condition=condition)

if __name__ == '__main__':
  import pythoncom, time
  
  def testDialog(event, ao, *args, **kwargs):
    return True
  
  def testForeground(event, ao, *args, **kwargs):
    print 'test forground', ao.Name
    if ao.Name is None:
      return False
    elif ao.Name.find('Notepad') > -1:
      return True
    
  def dialog(ao, *args, **kwargs):
    print 'see dialog start:', ao.Name
  
  def notepad(ao, *args, **kwargs):
    pid, tid = ao.ProcessID
    print 'see notepad in foreground', ao.Name, pid
    c = addCondition(pyAA.Constants.EVENT_SYSTEM_DIALOGSTART, testDialog, pid)
    c.setListener(dialog)
    
  c = addCondition(pyAA.Constants.EVENT_SYSTEM_FOREGROUND, testForeground, remove=True)
  c.setListener(notepad)
  
  while 1:
    pythoncom.PumpWaitingMessages()
    time.sleep(0.001)
