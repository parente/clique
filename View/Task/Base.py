'''
Defines the parent class for all task level patterns.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import weakref
import Constants
import Input, Output, Support, View

class Task(View.Base):
  '''
  Base class for all task level interaction patterns.
  
  @ivar tready: Has the task obtained its model or does it not require a model
    before interaction?
  @type tready: boolean
  @ivar first_announce: Has this task been announced yet?
  @type first_announce: boolean
  @cvar Permanence: Is this task startable or stoppable?
  @type Permanence: integer
  @cvar Modal: Is this task exclusive when it runs?
  @type Modal: boolean
  @cvar Successor: Task to start automatically when this one completes
  @type Successor: L{Task.Base.Task} 
  @cvar StartMacro: Macro to run at task start-up
  @type StartMacro: L{UIA.Macro.Macro}
  @cvar CancelMacro: Macro to run at task cancelation
  @type CancelMacro: L{UIA.Macro.Macro}
  @cvar CompleteMacro: Macro to run at task completion
  @type CompleteMacro: L{UIA.Macro.Macro}
  '''
  Modal = False
  Permanence = False
  Successor = None
  StartMacro = None
  CancelMacro = None
  CompleteMacro = None
  
  def __init__(self, parent, model):
    '''
    Initialize the object.
    
    See instance variables for parameter descriptions.
    '''
    super(Task, self).__init__(parent, model)
    self.tready = (self.Permanence & Constants.NO_START) and True
    self.first_announce = True
    
  def GetContainer(self):
    '''
    Asks the parent of this object to return its container. The base 
    implementation recursively calls this method on the object's parent. 
    Override in a subclass to determine the stopping condition.
    
    @return: Container of this L{Task} that determines to which set of L{Task}s
        it belongs
    @rtype: L{Task}
    '''
    return self.parent.GetContainer()

  def Output(self, source, packets):
    '''
    Passes audio output to the parent program. If the object sending the output 
    is not in focus, demote the output to the active program speaker.
    
    @param source: Object that called this output method
    @type source: L{Output.Manager.Pipe}
    @param packets: Collection of output packets
    @type packets: tuple or single L{Output.Messages.OutboundPacket}
    '''
    try:
      len(packets)
    except:
      packets = (packets,)    
    for packet in packets:
      if packet and source != self and source != self.focus:
        packet.RouteTo(Output.ACTIVE_PROG)
    self.parent.Output(self, packets)
    
  def IsValid(self):
    '''
    Virtual method. Override in a subclass to check if the current task state 
    allows it to be completed. Return a string to report if the state is invalid
    and needs to be corrected before the task can complete. Return None to 
    indicate the task is ready to complete.
    
    @return: None
    @rtype: None
    '''
    return None
    
  def OnInit(self):
    '''Virtual method. Called when the constructor completes.'''
    pass

  def OnStart(self, message):
    '''
    Checks if the task is startable or if a start macro has been defined.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.Permanence & Constants.NO_START:
      return
    else:
      self.OnReadyToStart(message)
      
  def OnDoThat(self, message):
    '''
    Treats a do that command as a request to end the task. Override in a 
    subclass to define a different behavior.

    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    if message.Press:
      self.OnImDone(message)
      
  def OnImDone(self, message):
    '''
    Checks if the task is completable and if the current state is valid for
    completion. Deactivates the control with the focus and calls 
    L{OnReadyToComplete) to execute any completion macro.
       
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.Permanence & (Constants.NO_COMPLETE):
      p = self.OutPermanence(message)
      self.Output(self, p)
      return
    text = self.IsValid()
    if text is None:
      try:
        self.focus.OnDeactivate(message)
      except AttributeError:
        pass
      self.OnReadyToComplete(message)
    else:
      p = self.OutInvalid(message, text)
      self.Output(self, p)

  def OnEscape(self, message):
    '''
    Checks if the task is cancelable. Deactivates the control with the focus and
    calls L{OnReadyCancel} to execute any cancellation macro.
       
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.Permanence & (Constants.NO_CANCEL):
      p = self.OutPermanence(message)
      self.Output(self, p)
      return
    else:
      try:
        self.focus.OnDeactivate(message)
      except AttributeError:
        pass
      self.OnReadyToCancel(message)
      
  def OnReadyToStart(self, message):
    '''
    Virtual method. Executes the start macro if one is defined, or calls 
    OnModelReady immediately. Override this to perform some action when the 
    task is starting, but before the model is established.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}    
    '''
    if self.StartMacro is not None:
      m = self.StartMacro(self, message, self.model)
      result = m.Execute()
      result.AddCallback(self.OnModelReady)
    else:
      self.OnModelReady(self.model, message)
      
  def OnReadyToComplete(self, message):
    '''
    Virtual method. Executes the completion macro if one is defined, or calls 
    OnComplete immediately. Override this to perform some action when the 
    task is about to complete.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    self.ready = False
    if self.CompleteMacro is not None:
      m = self.CompleteMacro(self, message, self.model)
      result = m.Execute()
      result.AddCallback(self.OnComplete)
    else:
      m = self.OnComplete(self.model, message)
    
  def OnReadyToCancel(self, message):
    '''
    Virtual method. Executes the cancelation macro if one is defined, or calls 
    OnCancel immediately. Override this to perform some action when the 
    task is about to cancel.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}    
    '''
    self.ready = False
    if self.CancelMacro is not None:
      m = self.CancelMacro(self, message, self.model)
      result = m.Execute()
      result.AddCallback(self.OnCancel)
    else:
      m = self.OnCancel(self.model, message)
    
  def OnReadyToUse(self, message):
    '''
    Virtual method. Override this to perform some action just after the model
    has been established, but before the task is activated.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    pass

  def OnComplete(self, result, message):
    '''
    Terminates the task sucessfully.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param result: Result of the macro that called this method, probably None
    @type result: object
    '''
    p = self.OutComplete(message)
    self.Output(self, p)
    # end the task and return either the last result or the final model
    self.parent.EndObject(message, self, result or self.model, True)
    
  def OnCancel(self, result, message):
    '''
    Terminates the task by cancelation.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param result: Result of the macro that called this method, probably None
    @type result: object
    '''
    p = self.OutCancel(message)
    self.Output(self, p)
    self.parent.EndObject(message, self, result or self.model, False)

  def OnModelReady(self, model, message):
    '''
    Activates the task after model object has been established.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}    
    @ivar model: Model driving this view
    @type model: L{Interface.IContext}
    '''
    # store the model and note it is ready
    self.model = model
    self.tready = True
    # call method to do preprocessing before activation
    self.OnReadyToUse(message)
    # reactivate the task
    self.OnActivate(message, False)

  def OnActivate(self, message, auto_focus):
    '''
    Handle a request to activate this pattern. Give the connected object the 
    focus.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: True if the task is ready for interaction, false if not
    @rtype: boolean
    '''
    if (super(Task, self).OnActivate(message, auto_focus) or self.model is None) \
       and self.tready:
      self.ready = True
      self.OnGainFocus(message)
      # play the introductory announcement
      p = self.OutIntroduction(message, auto_focus)
      self.Output(self, p)
      return True
    else:
      # play the waiting drum loop
      p = self.OutWaiting(message, auto_focus)
      self.Output(self, p)
    return False
    
  def OutWaiting(self, message, auto_focus):
    '''
    Outputs the waiting sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.CONTEXT)
    p.AddMessage(sound=Output.ISound(self).State('waiting'), 
                 person=Output.LOOPING)
    return p
   
  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the start or continue task sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    if self.first_announce:
      # play a sound indicating the task started      
      p = Output.Packet(self, message, Output.CONTEXT)
      p.AddMessage(sound=Output.ISound(self).Action('start'))
      self.first_announce = False
    elif not auto_focus:
      # play a sound indicating the task resumed
      p = Output.Packet(self, message, Output.CONTEXT)
      p.AddMessage(sound=Output.ISound(self).Action('resume'))
    else:
      return None
    # play the task identity sound
    p.AddMessage(sound=Output.ISound(self).Identity('task'), 
                 person=Output.INTERMITTENT)
    return p
    
  def OutComplete(self, message):
    '''
    Outputs the completion of task sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.CONTEXT)
    p.AddMessage(sound=Output.ISound(self).Action('complete'))
    return p
  
  def OutInvalid(self, message, text):
    '''
    Outputs the task refusal sound and a message explaining why an operation is
    invalid.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Message explaining why the task cannot complete
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}    
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).Warn('refuse'),
                 person=Output.SUMMARY,
                 speech=text)
    return p
  
  def OutPermanence(self, message):
    '''
    Outputs a message explaining the permanence of this task.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    if (self.Permanence & Constants.NO_CANCEL and 
        self.Permanence & Constants.NO_COMPLETE):
      return self.OutInvalid(message, 'This task cannot be completed '
                             'or canceled.')
    elif (self.Permanence & Constants.NO_CANCEL):
      return self.OutInvalid(message, 'This task cannot be canceled, '
                             'only completed.')
    elif (self.Permanence & Constants.NO_COMPLETE):
      return self.OutInvalid(message, 'This task cannot be completed, '
                             'only canceled.')
    return None
    
  def OutCancel(self, message):
    '''
    Outputs the task canceled sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.CONTEXT)
    p.AddMessage(sound=Output.ISound(self).Action('cancel'))
    return p
    
  def OutWhereAmI(self, message):
    '''
    Outputs the name and sound of the tree.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    if self.Name:
      p = super(Task, self).OutWhereAmI(message)
      s = 'in the %s task' % self.Name
      p.AddMessage(speech=s, sound=Output.ISound(self).Identity(),
                 person=Output.SUMMARY)
      return p
