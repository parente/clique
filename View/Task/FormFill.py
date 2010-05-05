'''
Defines classes for the pattern of filling out a form of fields.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import Base, Output, Config, System

class FormFill(Base.Task):
  '''
  Pattern to support the linear navigation through a list of control patterns.
  
  @ivar wait_done: Time of last message indicating waiting to complete task
  @type wait_done: float
  @ivar curr: Index of the active field
  @type curr: number
  @ivar fields: All the form fields
  @type fields: list of L{Control.Base}
  '''
  def __init__(self, parent, model):
    super(FormFill, self).__init__(parent, model)
    self.curr = 0
    self.fields = []
    self.wait_done = None
    
  def Shutdown(self):
    '''Calls shutdown on all controls.'''
    for f in self.fields:
      f.Shutdown()
    super(FormFill, self).Shutdown()
    
  def GetSize(self):
    '''
    @return: Total number of views
    @rtype: number
    '''
    return len(self.fields)
  Size = property(GetSize)
  
  def AddField(self, field):
    '''
    Adds a field to the list of navigable fields.
    
    @param field: Some control that acts as a field in the form
    @type field: L{Control.Base.Control}
    '''
    self.fields.append(field)

  def PopField(self):
    '''
    Removes the last added field and returns it.

    @return: Some control that acts as a field in the form
    @rtype: L{Control.Base.Control}
    '''
    return self.fields.pop()
    
  def OnActivate(self, message, auto_focus):
    '''
    Handle a request to activate this task. Ensure the connection is ready 
    before proceeding.
    
    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: True if the task is ready for interaction, false if not
    @rtype: boolean
    '''
    if super(FormFill, self).OnActivate(message, auto_focus):
      self.ChangeFocus(self.fields[self.curr], None, auto_focus)
      return True
    else:
      return False

  def OnPrevSubTask(self, message):
    '''
    Handle a request to activate the previous field.
    
    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    m = message
    wrap = False
    for i in range(1, self.Size):
      c = (self.curr - i) % self.Size
      # did we wrap?
      if self.curr - i < 0:
        p = Output.Packet(self, message, Output.CONTEXT)
        p.AddMessage(sound=Output.ISound(self).Action('wrap'))
        self.Output(self, p)
      if self.ChangeFocus(self.fields[c], m, False):
        # the field accepted the focus
        self.curr = c
        return
      else:
        # the field rejected the focus, try the previous one
        p = self.fields[c].OutDeadShort(message)
        m = None
        self.Output(self, p)

  def OnNextSubTask(self, message):
    '''
    Handle a request to activate the next field. Ensure the connection is ready
    before proceeding.
    
    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    print 'on next subtask'
    m = message
    for i in range(1, self.Size):
      c = (self.curr + i) % self.Size
      if self.curr + i >= self.Size:
        p = Output.Packet(self, message, Output.CONTEXT)
        p.AddMessage(sound=Output.ISound(self).Action('wrap'))
        self.Output(self, p)
      if self.ChangeFocus(self.fields[c], m, False):
        # the field accepted the focus
        self.curr = c
        return
      else:
        # the field rejected the focus, try the previous one
        p = self.fields[c].OutDeadShort(message)        
        m = None
        self.Output(self, p)
        
  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the control type and the number of fields.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p1 = super(FormFill, self).OutIntroduction(message, auto_focus)
    p2 = Output.Packet(self, message)
    if self.Size > 1:
      speech = '%s, %d fields' % (self.Name, self.Size)
    else:
      speech = self.Name
    p2.AddMessage(speech=speech, person=Output.SUMMARY)
    return (p1, p2)
