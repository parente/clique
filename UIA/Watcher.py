'''
Defines an event monitor that notes the last time an event occurred in a given
process.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import time, pyAA

class StabilityWatcher(object):
  '''
  Watches for all events coming from a process. Tracks the time since the last 
  event as a way of detecting stability in an application. Implemented as a 
  separate thread with its own message loop to allow event notifications even 
  while the main thread is busy processing input messages.

  @ivar LastTime: Time of the last disturbance to the program
  @type LastTime: integer
  @ivar watcher: Watcher that monitors all events
  @type watcher: pyAA.Watcher
  @ivar pid: Process ID to watch
  @type pid: integer
  ''' 
  def __init__(self, pid):
    '''
    Initialize an instance.
    
    @param pid: Process to watch
    @type pid: integer
    '''
    super(StabilityWatcher, self).__init__()
    self.LastTime = time.time()
    self.LastStable = self.LastTime
    self.pid = pid
    self.watcher = pyAA.Watcher()
    self.watcher.AddWinEventHook(callback=self.Disturb, process_id=self.pid)    
      
  def Destroy(self):
    '''Shuts down the message pump.'''
    self.watcher.Release()

  def Disturb(self, event=None):
    '''Sets the last event time to the current time.'''
    self.LastTime = time.time()
