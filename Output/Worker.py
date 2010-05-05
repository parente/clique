'''
Defines classes to support asynchronous output using threads.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import threading

class Barrier(object):
  '''  
  Encapsulates an atomic counter that keeps track of how many threads have
  arrived at the barrier.
  
  @ivar lock: Used to ensure atomic counts
  @type lock: threading.Lock
  @ivar value: Number of threads yet to arrive at the barrier
  @type value: number
  '''
  def __init__(self, value):
    '''
    Initialize the object.
    
    @param value: Number of threads expected to arrive at the barrier
    @type value: number
    '''
    self.lock = threading.Lock()
    self.value = value
    
  def Arrive(self):
    '''Arrive at the barrier by decreasing value by one.'''
    self.lock.acquire()
    self.value -= 1
    self.lock.release()
    
  def IsDone(self):
    '''
    @return: Have all expected threads arrived?
    @rtype: boolean
    '''
    return self.value <= 0

class Worker(threading.Thread):
  '''  
  Parent class for all threads that process output messages. Provides a thread
  loop that calls a number of virtual methods that should handle output events.
  
  @ivar alive: Should the thread continue running?
  @type alive: boolean
  @ivar preempt: Event signaling if messages should be pre-empted
  @type preempt: threading.Event
  @ivar plock: Lock around pre-empting and retrieving messages
  @type plock: threading.Lock
  @ivar incoming: Placeholder for incoming events
  @type incoming: None
  '''
  def __init__(self):
    '''Initialize an instance.'''
    threading.Thread.__init__(self)
    self.alive = True
    self.plock = threading.Lock()
    self.preempt = threading.Event()
    self.incoming = None    
    
  def Destroy(self):
    '''Quit our thread loop.'''
    self.alive = False
    
  def run(self):
    '''
    Main thread loop waits for events, processes them, waits for a response, and
    then completes processing. The methods called must be overridden to do any
    real work.
    '''
    while self.alive:
      event = self.WaitForEvent()
      if event is None: continue
      if not self.HandleEvent(*event): continue
      if not self.WaitWhileProcessing(*event): continue
      self.CompleteEvent(*event)
      
  def WaitForEvent(self):
    '''Virtual method. Called to get an event from some source.
    
    @return: Event object or None to skip processing
    @rtype: None
    '''
    return None
    
  def HandleEvent(self, *event):
    '''Virtual method. Called to process an event.
    
    @param event: Objects returned by the WaitForEvent method
    @type event: list
    @return: True if processing should continue, False if not
    @rtype: boolean
    '''
    return True
    
  def WaitWhileProcessing(self, *event):
    '''
    Virtual method. Called to wait while asynchronous processing is occurring.
        
    @param event: Objects returned by the WaitForEvent method
    @type event: list
    @return: True if processing should continue, False if not
    @rtype: boolean    
    '''
    return True
    
  def CompleteEvent(self, *event):
    '''Virtual method. Called after processing has finished.
        
    @param event: Objects returned by the WaitForEvent method
    @type event: list
    '''
    pass
    
  def Play(self, *args):
    '''Virtual method. Called to add an event to be processed.
    
    @param args: Event related data
    @type args: list
    '''
    pass
