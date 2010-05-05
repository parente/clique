'''
Defines the most-base class for all IO view objects in the system.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import weakref
import Output, Input, Interface, Support

# internal object messages
SYS_INDIRECT_CHANGE = Input.Constants.GenCommandID()

# add mappings from automation messages to methods
cmd_dispatch = {SYS_INDIRECT_CHANGE : 'OnIndirectChange'}
Input.Constants.AddDispatch(cmd_dispatch)

class Base(Output.Pipe, Input.Pipe):
  '''
  Most base class for IO objects in the system. Stores a model that drives the
  input and output from this object. Maintains a collection of weak refernces
  to listeners interested in changes in this object.
  
  @ivar options: Context chooser options
  @type options: list
  @ivar model: Model represented by this view
  @type model: object
  @cvar Name: Name of this view object
  @type Name: string
  '''
  Name = ''
  
  def __init__(self, parent, model):
    '''
    Initialize an instance by establishing the input and output pipeline.
    
    See instance variables for parameter descriptions.
    '''
    Input.Pipe.__init__(self)
    Output.Pipe.__init__(self, parent)
    self.model = model
    self.options = []
    self.change_listeners = weakref.WeakKeyDictionary()
    
  def __del__(self):
    print '*** destroyed view %s ***' % self.Name
    
  def Pause(self):
    '''
    Sets the ready flag to False so that this control is disabled and will not
    process user input.
    '''
    self.ready = False
  
  def Unpause(self, *args, **kwargs):
    '''
    Sets the ready flag to True so that this control is enabled to receive
    input. Any number of args or kwargs can be given and will be ignored 
    allowing this method to serve as a callback function to L{UIA.Macro}s if
    desired.
    '''
    self.ready = True

  def GetID(self):
    '''
    @return: ID unique across all automated objects
    @rtype: integer
    '''
    return id(self)
  ID = property(GetID)
  
  def GetModel(self):
    '''
    @return: Model held by this view
    @type: object
    '''
    return self.model

  def SetModel(self, model):
    '''
    @param model: Model to be held by this view
    @type model: object
    '''
    self.model = model
  Model = property(GetModel, SetModel)
  
  def Shutdown(self):
    '''
    Removes all context options to ensure that the there are no cyclic 
    references between an object and its condition functions.
    '''
    self.ClearContextOptions()
    
  def AddContextOption(self, cls, own, cond=lambda: True):
    ''''
    Add a task that can be started in this context.
    
    @param cls: Task class that can be started
    @type cls: L{View.Base.Base}
    @param own: Should we own this class?
    @type own: boolean
    @param cond: Precondition necessary for the task to start
    @type cond: callable
    '''
    self.options.append(Support.Bag(Class=cls, Owned=own, Condition=cond))
    
  def ClearContextOptions(self):
    '''
    Clears all context options. Useful for making sure there are no strong 
    references to conditions that may cause a L{View} to avoid garbage 
    collection even when it is no longer needed.
    '''
    self.options = []
  
  def AddChangeListener(self, obj):
    '''
    Add an object to the listeners list.
    
    @param obj: Any object that can receive updates about an event
    @type obj: L{View.Base}
    '''
    self.change_listeners[obj] = None
    
  def NotifyAboutChange(self):
    '''
    Inform listeners about a change in state.
    '''
    # get strong references to the listeners before iterating
    listeners = self.change_listeners.keys()
    im = Input.Manager()
    for obj in listeners:
      # route a message to an observer
      message = Input.InboundMessage(SYS_INDIRECT_CHANGE)
      message.RouteTo(weakref.proxy(obj))
      im.AddMessage(message)
    # strong references are released when this method ends
    
  def OnActivate(self, message, auto_focus):
    '''
    Readies this object for interaction.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did the object receive focus automatically?
    @type auto_focus: boolean
    @return: Did the model activate?
    @rtype: boolean
    '''
    super(Base, self).OnActivate(message, auto_focus)
    try:
      return Interface.IInteractive(self.model).Activate()
    except NotImplementedError:
      return False
    
  def OnDeactivate(self, message):
    '''
    Deactivates this object.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    super(Base, self).OnDeactivate(message)
    if self.model is not None:
      Interface.IInteractive(self.model).Deactivate()
    self.OnLoseFocus(message)
    
  def OnGainFocus(self, message):
    '''
    Virtual method. Executes script code when the object is ready and gets the
    focus. Override this, not OnActivate.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    pass
    
  def OnLoseFocus(self, message):
    '''
    Virtual method. Executes script code when the object loses the focus.
    Override this, not OnDeactivate.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    pass
    
  def OnWhereAmI(self, message):
    '''
    Reports information about the active object.
    
    Calls OutWhereAmI.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    '''
    p = self.OutWhereAmI(message)
    self.Output(self, p)
    # allow the message to propogate so other objects can report too
    message.Stop = False
    
  def OnChooseTask(self, message):
    '''
    Attaches context options to the message and allows it to propogate.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    bag = Support.Bag()
    if message.Seen:
      bag.Options = message.UserData.Options + self.options
    else:
      bag.Options = self.options
    bag.Source = self
    message.UserData = bag
    message.Stop = False

  def OutWhereAmI(self, message):
    '''
    Virtual method. Override to report information about the active object.
    
    @param message: Input message that caused the change in state
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    if message.Seen: 
      msg = None
    else: 
      msg = message
    # return an empty packet with an input message only if this is the first
    # object to see that message; avoids preemption of output
    return Output.Packet(self, msg)
    
if __name__ == '__main__':
  pass
