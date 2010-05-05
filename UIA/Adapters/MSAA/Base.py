'''
Defines base classes for MSAA adapters.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import protocols, pyAA, weakref
import View
from Interface import IInteractive, IContext
from protocols import advise
from Constants import *

class Adapter(object):
  '''
  Base class for all MSAA adapters. Gets object at the given path from the 
  IContext implementation.
  
  @ivar context: Context in which the control is located
  @type: L{Interface.IContext}
  @ivar path: Path to the control rooted at the context object
  @type path: string
  @ivar subject: Accessible being adapted to a particular interface
  @type subject: pyAA.AccessibleObject
  '''
  def __init__(self, context, path):
    self.context = weakref.proxy(context)
    self.path = path
    self.subject = None
    
  def Activate(self):
    '''
    Queries the context for the object at the given path. 
    
    @return: Was the subject retrieved?
    @type: boolean
    '''
    self.subject = IContext(self.context).GetObjectAt(self.path)
    print '***', self.subject
    return self.subject is not None
    
  def Deactivate(self):
    '''Does nothing.'''
    return
  
  def HasChanged(self):
    '''
    Checks if the subject is still valid. If not, indicates the model has 
    changed. If the new model cannot be activated, indicate that the model has
    not changed.
    
    @return: Is the previously held subject invalid?
    @rtype: boolean
    '''
    try:
      self.subject.Name
    except (pyAA.Error, AttributeError):
      # activate the new model if possible
      if self.Activate():
        return True
    return False
  
  def GetName(self, override, default):
    '''
    Gets the name for this object. If override is specified by the L{View}, hand
    that back immediately. Otherwise, try to get the name of the subject. If 
    that name is blank or unavailable, use the default.
    
    @param override: Name specified by the L{View}
    @type override: string
    @param default: Default name for the L{View}
    @type default: string
    @return: Name of this model
    @rtype: string
    '''
    if not override:
      try:
        return self.subject.Name or default
      except (pyAA.Error, AttributeError):
        return default
    else:
      return override
    
class ContextForView(protocols.Adapter):
  advise(instancesProvide=[IContext], asAdapterForTypes=[View.Base])
  
  def GetObjectAt(self, path): 
    '''
    Retrieves the object at the given path within this content.
    
    @param path: Path to the desired object
    @type path: string
    @return: Object at the given path or None if dead
    @rtype: pyAA.AcessibleObject
    '''
    try:
      model = self.subject.Model
      print '*** adapter:', model.RoleText, model.Name
      return model.ChildFromPath(path)
    except pyAA.Error:
      return None
    
class AccessibleForTask(protocols.Adapter):
  '''
  Contents containing objects that can be retrieved and adapted to various
  interfaces. Represents a root from which paths to child objects step
  '''
  advise(instancesProvide=[IInteractive],
         asAdapterForTypes=[pyAA.AccessibleObject])
                           
  def Activate(self):
    '''Gives the subject the focus.'''
    try:
      self.subject.Select(FOCUS)
      return True
    except pyAA.Error:
      return False
    
  def Deactivate(self):
    '''Does nothing.'''
    pass
  
  def HasChanged(self):
    '''
    Tasks do not currently support indirect changes.
    
    @return: Always False
    @rtype: boolean
    '''
    return False
  
  def GetName(self, override, default):
    '''
    Gets the name of the L{View.Task} as the name of this model.
    
    @param override: Name specified by the L{View}
    @type override: string
    @param default: Default name for the L{View}
    @type default: string  
    @return: Override or default depending on what's available
    @rtype: string
    '''
    return override or default
