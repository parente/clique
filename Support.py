'''
Defines miscellaneous supporting classes, functions, and decorators.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import win32pdh
import weakref
import Interface
from protocols import advise

class Bag(object):
  '''
  Holds information in instance variables. Returns None rather than an exception
  if a named variable does not exist.
  '''
  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)
  
  def __getattr__(self, name):
    try:
      return self.__dict__[name]
    except KeyError:
      return None

class Null(object):
  '''
  Placeholder for a connection to an object that cannot be established because 
  the object does not exist. 
  
  An implementation of the Null object design pattern based on the code provided 
  by Dinu C. Gherman at 
  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/68205.
  '''
  advise(instancesProvide=[Interface.IInteractive],
         asAdapterForTypes=[type(None)])
         
  def __init__(self, *args, **kwargs):
    self.__dict__.update(kwargs)
  def __call__(self, *args, **kwargs):
    return self
  def __iter__(self):
    return iter([])
  def __getattr__(self, mname):
    if self.__dict__.has_key(mname):
      return self.__dict__[mname]
    else:
      return self
  def __setattr__(self, name, value):
    return self
  def __delattr__(self, name):
    return self
  def __repr__(self):
    return ''

class MethodGeneratorProxy(object):
  '''
  Wraps a generator method in a callable. On each call to an instance of this
  class, one of the following occurs: the generator advances one iteration and
  its result is returned, the generator is reset and None is returned, or the
  generator throws a StopIteration (which is caught) and None is returned.
  The generator is automatically re-instantiated on the next call after the
  StopIteraction exception is raised.

  This class does not maintain a strong reference to the object to which the
  method is attached. It will not impede garbage collection.

  @ivar func: Method that, when called, instantiates a generator
  @type func: function
  @ivar gen: Instantiated generator
  @type gen: generator
  @ivar reset_flag: Param to look for in keyword args as the signal to reset
  @type reset_flag: string
  '''
  def __init__(self, func, reset_flag):
    '''
    Initializes an instance.

    See instance variables for parameter descriptions.
    '''
    self.func = func
    self.gen = None
    self.reset_flag = reset_flag

  def __call__(self, obj, *args, **kwargs):
    '''
    Generate the next item or reset the generator.

    @param obj: Object to which the generator is attached
    @type obj: object
    @param args: Positional arguments to the generator method
    @type args: list
    @param kwargs: Keyword arguments to the generator method
    @type kwargs: dictionary
    '''
    if kwargs.get(self.reset_flag):
      # reset the generator and return None
      self.gen = None
      return None
    elif self.gen is None:
      # create a new generator
      try:
        wobj = weakref.proxy(obj)
      except TypeError:
        wobj = obj
      self.gen = self.func(wobj, *args, **kwargs)

    try:
      # generate next item
      return self.gen.next()
    except StopIteration:
      # destroy the generator and return None
      self.gen = None
      return None

def generator_method(cls_name, reset_flag='reset_gen'):
  '''
  Decorator for methods that act as generators. Methods decorated as such can
  be called like normal methods, but can (and should) include yield statements.
  The parameters passed to the first invocation of the method are used for all
  subsequent calls until the generator is reset.

  Generator methods can be overriden in subclasses as long as the name provided
  is unique to each class in the inheritence tree (i.e. make it the name of the
  class and everything will work fine.

  To reset a generator method, pass True in a keyword argument with the name
  specified in reset_flag. Generator methods in parent classes must be reset
  explicitly (i.e. Parent.MethodName(self, reset_gen=True).

  @param cls_name: Name unique to the inheritence tree of this class
  @type cls_name: string
  @param reset_flag: Name of a parameter that will reset the generator
  @type reset_flag: string
  '''
  # define another function that takes just the function as an argument
  # we must do this to deal with the fact that we need the name argument above
  def generator_method_internal(func):
    # build a name for the method generator
    name = '_%s_%s_gen_proxy_' % (cls_name, func.func_name)
    # define a replacement for a method that calls the generator instead
    def generator_method_invoke(obj, *args, **kwargs):
      try:
        # try to get a generator defined for the called method
        gen = getattr(obj, name)
      except AttributeError:
        # build a new generator for the called method
        gen = MethodGeneratorProxy(func, reset_flag)
        setattr(obj, name, gen)
      # call the generator and return its result
      return gen(obj, *args, **kwargs)
    # return our wrapping for the method
    return generator_method_invoke
  # return the true decorator for the method
  return generator_method_internal

def GetPIDs():
  '''
  Returns process IDs for all running processes on the system.
  
  @return: Dictionary with keys as PIDs and values as None
  @rtype: dictionary
  '''
  counts = {}
  handles = []
  procs = {}
  # get names of all running procs
  items, instances = win32pdh.EnumObjectItems(None, None, 'Process', 
                                              win32pdh.PERF_DETAIL_WIZARD)
  # start a new query
  hq = win32pdh.OpenQuery()
  # iterate over all running procs
  for instance in instances:
    # keep track of indices into procs of the same name
    counts[instance] = counts.setdefault(instance, 0) + 1
    path = win32pdh.MakeCounterPath((None, 'Process', instance, None, 
                                     counts[instance]-1, 'ID Process'))
    # add queries for pid
    handles.append(win32pdh.AddCounter(hq,path))
  # collect all pids
  win32pdh.CollectQueryData(hq)
  for hc in handles:
    # put PIDs into a dict indexed by PID
    try:
      type,val=win32pdh.GetFormattedCounterValue(hc,win32pdh.PDH_FMT_LONG)
    except:
      # continue on any kind of error
      continue
    procs[val] = None
    win32pdh.RemoveCounter(hc)
  # close the query and return the dict
  win32pdh.CloseQuery(hq)
  return procs
  
if __name__ == '__main__':
  print GetPIDs()
