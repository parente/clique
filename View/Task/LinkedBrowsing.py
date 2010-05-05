'''
Defines classes for the pattern of browsing a number of dyanmic views.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import Base, Output, System, Config

class LinkedBrowsing(Base.Task):
  '''
  Pattern to support the linear navigation through a list of control patterns.
  
  @ivar wait_done: Time of last message indicating waiting to complete task
  @type wait_done: float
  @ivar curr: Index of the active field
  @type curr: number
  @ivar fields: All the views
  @type fields: list of L{Control.Base}
  '''  
  def __init__(self, parent, model):
    super(LinkedBrowsing, self).__init__(parent, model)
    self.views = []
    self.curr = 0
    self.wait_done = None
    
  def Shutdown(self):
    '''Calls shutdown on all views.'''
    for v in self.views:
      v.Shutdown()
    super(LinkedBrowsing, self).Shutdown()
    
  def GetSize(self):
    '''
    @return: Total number of views
    @rtype: number
    '''
    return len(self.views)
  Size = property(GetSize)
  
  def AddView(self, view):
    '''
    Add a view to this task. Connect the added view to a previous view to receive
    update messages if that view exists.
    
    @param view: Some control
    @type view: L{Control.Base.Control}
    '''
    if self.Size > 0:
      # connect this view to the previous for change notifications
      self.views[-1].AddChangeListener(view)
    self.views.append(view)
    
  def OnDoThat(self, message):
    '''
    Moves the focus to the next field in the sequeunce or completes the task 
    if there is only one field.

    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    if message.Press:
      self.OnImDone(message)

  def OnActivate(self, message, auto_focus):
    '''
    Handle a request to activate this task. Ensure the model is ready before
    proceeding.
    
    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: True if the task is ready for interaction, false if not
    @rtype: boolean
    '''    
    if Base.Task.OnActivate(self, message, auto_focus):
      self.ChangeFocus(self.views[self.curr], None, auto_focus)
      return True
    else:
      return False
    
  def OnPrevSubTask(self, message):
    '''
    Handle a request to activate the previous field.
    
    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.curr-1 < 0:
      p1 = Output.Packet(self, message, Output.CONTEXT)
      p1.AddMessage(sound=Output.ISound(self).Action('wrap'))
      self.Output(self, p1) 
    self.curr = (self.curr-1) % self.Size
    if not self.ChangeFocus(self.views[self.curr], message, False):
      p2 = self.views[self.curr].OutDeadLong(message)
      self.Output(self, p2)

  def OnNextSubTask(self, message):
    '''
    Handle a request to activate the next field.
    
    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.curr+1 >= self.Size:
      p1 = Output.Packet(self, message, Output.CONTEXT)
      p1.AddMessage(sound=Output.ISound(self).Action('wrap'))
      self.Output(self, p1)
    self.curr = (self.curr+1) % self.Size
    if not self.ChangeFocus(self.views[self.curr], message, False):
      p2 = self.views[self.curr].OutDeadLong(message)
      self.Output(self, p2)
      
  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the control type and the number of views.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p1 = super(LinkedBrowsing, self).OutIntroduction(message, auto_focus)
    p2 = Output.Packet(self, message)
    p2.AddMessage(speech='%s, %d views' % (self.Name, self.Size), 
                  person=Output.SUMMARY)
    return (p1, p2)
