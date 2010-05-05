'''
Defines classes for no interaction patterns.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import Base, Constants, Output

class RunAndReport(Base.Task):
  '''
  Pattern to support the running of a macro without any user interaction or 
  reporting on the part of the task. Runs the start macro and then the
  completion or cancellation macro. Plays the waiting sound in the mean time.
  ''' 
  def OnActivate(self, message, auto_focus):
    '''
    Handles a request to activate this task. While the task is busy executing
    the start macro, plays the waiting sound. Once the start macro is done, 
    it either completes or cancels based on the L{Permanence} settings for the
    task.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: True if the task is ready for interaction, false if not
    @rtype: boolean
    '''
    if self.tready:
      # immediately quit once ready
      if self.Permanence & Constants.NO_COMPLETE:
        print '******** cancelling'
        self.OnReadyToCancel(message)
      else: 
        self.OnReadyToComplete(message)
      return False
    else:
      # play the waiting drum loop
      p = self.OutWaiting(message, auto_focus)
      self.Output(self, p)
      return False

class RunWaitReport(RunAndReport):
  '''
  Pattern to support the running of a macro without any user interaction or 
  reporting on the part of the task. Runs the start macro and then the
  completion or cancellation macro. Plays the waiting sound and speaks the name
  of the task in the mean time.
  '''
  def OutWaiting(self, message, auto_focus):
    '''
    Outputs the waiting sound and the name of the task while waiting.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p1 = Output.Packet(self, message, Output.CONTEXT)
    p1.AddMessage(sound=Output.ISound(self).State('waiting'), 
                  person=Output.LOOPING)
    p2 = Output.Packet(self, message)
    p2.AddMessage(speech=self.Name, person=Output.SUMMARY)
    return (p1, p2)
