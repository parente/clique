'''
Defines a base class for a mixin class that will have its methods automatically
added to that of another class once at runtime.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import new, types, re

class ClassMixer(object):
  '''  
  Wraps method calls in a class with methods defined in subclasses of this
  class. Rebuilds properties to ensure they point to wrapped methods.
  
  @ivar other: Class to modify
  @type other: class
  @ivar prefix: Text to be prepended to original method names when they are 
    modified
  @type prefix: string
  '''
  def __init__(self, other, prefix='mixed_'):
    '''
    Initialize an instance.
    
    See instance variables for parameter descriptions.
    '''
    self.other = other
    self.prefix = prefix

  def RegenProperties(self, new_meths):
    '''
    Rebuilds properties that may have had their get/set/del methods wrapped so
    that the properties now call the wrapped methods.
    
    @param new_meths: New methods keyed by original method name
    @type new_meths: dictionary
    '''
    # rebuild properties in the class
    for name in self.other.__dict__.keys():
      if isinstance(self.other.__dict__[name], property):
        op = self.other.__dict__[name]
        # only rebuild if the methods of the property have been touched
        if (op.fget is not None and new_meths.has_key(op.fget.func_name)) or \
          (op.fset is not None and new_meths.has_key(op.fset.func_name)) or \
          (op.fdel is not None and new_meths.has_key(op.fdel.func_name)):
          # create a new property pointing to the new methods
          try: g = new_meths[op.fget.func_name]
          except: g=None
          try: s = new_meths[op.fset.func_name]
          except: s=None
          try: d = new_meths[op.fdel.func_name]
          except: d = None
          setattr(self.other, name, property(fget=g, fset=s, fdel=d))

  def WrapMethods(self, wrapper, include=None, exclude=None):
    '''    
    Wraps methods named in include or those not in exclude, or all methods if
    both are None, with the callable returned by the function in parameter
    wrapper. Each wrapper method takes the name of the function it is wrapping
    and the prefix and is expected to return an callable that takes a variable
    number of positional and keyword arguments. The wrapper is responsible for
    calling the original function by its new name (i.e. prefix+name) if desired.
    For example,
    
    def MyWrapper(self, name, prefix):
      def PrintIt(self, *args, **kwargs):
        print args, kwargs
        r = getattr(self, prefix+name)(*args, **kwargs)
        print r
        return r
      return PrintIt
      
    @param wrapper: Callable that returns a wrapper callable
    @type wrapper: callable
    @param include: Method names to wrap
    @type include: list
    @param exclude: Method names to avoid wrapping
    @type exclude: list
    '''
    new_meths = {}

    # replace unbound methods with our wrapper
    for name in self.other.__dict__.keys():
      if isinstance(self.other.__dict__[name], types.FunctionType) and \
        not name.startswith(self.prefix) and \
        (include is None or name in include) and \
        (exclude is None or name not in exclude):
        # create an internal version of this method
        setattr(self.other, self.prefix+name, self.other.__dict__[name])
        # create a wrapper version of this method
        #method = new.instancemethod(wrapper(name, self.prefix), None, self.other)
        func = wrapper(name, self.prefix)
        method = new.function(func.func_code, func.func_globals, name,
                              func.func_defaults, func.func_closure)
        setattr(self.other, name, method)
        # store method locally in case it is referenced by a property
        new_meths[name] = method

    # regenerate properties in case their methods have changed
    self.RegenProperties(new_meths)

  def StirInto(self, include=None, exclude=None):
    '''    
    Adds the methods named in include or those not in exclude, or all methods if
    neither is specified, in a subclass of this class to the other class. The
    added methods are viable targets for wrapping after they are added.
    
    @param include: Method names to add
    @type include: list
    @param exclude: Method names to avoid adding
    @type exclude: list
    '''
    cls = self.__class__
    # add new methods to the class
    for name in cls.__dict__.keys():
      # add methods
      if isinstance(cls.__dict__[name], types.FunctionType) and \
        name not in ClassMixer.__dict__.keys() and \
        not name.endswith('Wrapper') and \
        (include is None or name in include) and \
        (exclude is None or name not in exclude):
        func = cls.__dict__[name]
        method = new.function(func.func_code, func.func_globals, name,
                              func.func_defaults, func.func_closure)
        setattr(self.other, name, method)
