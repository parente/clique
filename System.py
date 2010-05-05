'''
Defines the message pump for the Clique system.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import pythoncom
import Queue, traceback, time
import Config

def Sleep(wait):
  '''
  Sleeps for the given amount of time. Pumps system messages before and after
  sleeping.
  
  @param wait: Time to sleep in milliseconds
  @type wait: float
  '''
  pythoncom.PumpWaitingMessages()  
  time.sleep(wait)
  pythoncom.PumpWaitingMessages()

class Pump(object):
  '''
  Message pump for the Clique system. Processes Windows messages and trapped 
  keyboard events. Supports future calls to functions outside the class. 
  Implements the Singleton pattern.

  @cvar instance: Singleton instance
  @type instance: L{Manager}
  @ivar im: Manager for all system input
  @type im: L{Input.Manager}
  '''
  instance = None
  
  def __new__(cls, im=None):
    '''
    Initializes a single instance of a class and stores it in a class variable. 
    Returns that instance whenever this method is called again. Implements the 
    Singleton design pattern.
    
    @param im: Manager for all system input
    @type im: L{Input.Manager}
    @return: Instance of this class
    @rtype: L{Manager}
    '''
    # return an existing instance
    if cls.instance is not None:
      return cls.instance    
    # build and initialize a new instance
    self = object.__new__(cls)
    # store the instance for later
    cls.instance = self
    # hold a reference to the input manager
    self.im = im
    # create a sorted list of futures
    self.futures = []
    return self  
  
  def __init__(self, *args, **kwargs): pass

  def Start(self):
    '''Runs the message pump til death.'''
    alive = True
    
    # add a special startup event
    self.im.AddInformStartupMessage()
    
    # loop while the alive flag has been set
    while alive:
      Sleep(0.001)
      # dispatch input messages
      try:
        alive = self.im.ProcessMessages()
      except Exception:
        traceback.print_exc()
        if not Config.catch_exceptions: 
          self.im.Destroy()
          break
      # run registered futures
      while len(self.futures) and time.time() > self.futures[0][0]:
        t, func, args, kwargs = self.futures.pop(0)
        try:        
          func(*args, **kwargs)
        except Exception:
          traceback.print_exc()
          if not Config.catch_exceptions:
            self.im.Destroy()
            break
          
  def RegisterFuture(self, delta, func, *args, **kwargs):
    '''
    Registers a callable to be invoked at delta number of seconds in the future.
    
    @param delta: Number of seconds in the future to call the function
    @type delta: float
    @param func: Function to be called
    @type func: callable
    @param args: Arguments to be passed to the callback
    @type args: list
    @param kwargs: Keyword arguments to be passed to the callback
    @type kwargs: dictionary
    '''
    self.futures.append((time.time()+delta, func, args, kwargs))
    self.futures.sort()
