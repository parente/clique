'''
Defines classes for the pattern of completing a number of tasks sequentially.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import Base, Output

class Wizard(Base.Task):
  '''
  Linear sequence of tasks with an explicit start and end.
  
  @ivar steps: Collection of classes for steps in the wizard
  @type steps: list
  @ivar task: Running step in the wizard
  @type task: L{Task.Base.Task}
  @ivar pos: Current task index
  @type pos: integer
  '''
  def __init__(self, parent, model):
    '''
    Initialize the object.
    
    See instance variables for parameter descriptions.
    '''
    super(Wizard, self).__init__(parent, model)
    self.steps = []
    self.curr = 0
    self.task = None
    
  def GetSize(self):
    '''
    @return: Total number of steps
    @rtype: number
    '''
    return len(self.steps)
  Size = property(GetSize)

  def AddStep(self, task):
    '''
    Add a step to the wizard.
    
    @param field: Some control that acts as a field in the form
    @type field: L{Control.Base.Control}
    '''
    self.steps.append(task)
    
  def StartObject(self, message, factory, model):
    '''
    Starts a step in the wizard running.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param factory: Callable that creates the next step
    @type factory: class
    @param model: Model driving the new task view
    @type model: L{Interface.IContext}
    '''
    # create the task object
    t = factory(self, model)
    if self.Size > 1:
      # add the step number to the task name if more than one step
      t.Name = 'step %d of %d, %s' % (self.curr+1, self.Size, t.Name)
    # store the running task
    self.task = t
    # let the task initialize itself
    t.OnInit()
    # don't pass a message so the task's output queues instead of preempts
    # switch the focus to the new task immediately
    self.ChangeFocus(t, None, True)
    t.OnStart(None)
    
  def EndObject(self, message, task, model, completed):
    '''
    Ends the current step in the wizard. Either starts the next step, cancels
    the entire wizard, or completes the wizard.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param task: Task to end
    @type task: L{Task.Base.Task}
    @param model: Model driving the task view
    @type model: L{Interface.IContext}
    @param completed: Did the task complete (True) or was it canceled (False)?
    @type completed: boolean
    '''
    print 'task cancelled', completed
    task.Shutdown()
    if completed:
      # try to start the next task
      try:
        self.curr += 1
        self.StartObject(message, self.steps[self.curr], model)
        return
      except IndexError:
        # run the completion macro if done, do not check for uncompletable
        self.OnReadyToComplete(message)
    else:
      print 'cancelling wizard'
      # run the cancelation macro if canceled, do not check for uncancellable
      self.OnReadyToCancel(message)
  
  def OnModelReady(self, model, message):
    '''
    Stores the model for the wizard.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}    
    @param model: Model driving this view
    @type model: L{Interface.IContext}
    '''
    self.model = model
    self.tready = True
    # call method to do preprocessing before activation
    self.OnReadyToUse(message)
    # activate the wizard
    self.OnActivate(message, True)
    # start the first task
    self.StartObject(message, self.steps[self.curr], self.model)
    
  def OnActivate(self, message, auto_focus):
    if super(Wizard, self).OnActivate(message, auto_focus):
      if self.task is not None:
        self.ChangeFocus(self.task, message, auto_focus)
      return True
    else:
      return False
    
  def OutCancel(self, message):
    '''
    Outputs no sound on cancelation.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass
    
  def OutComplete(self, message):
    '''
    Outputs no sound on completion.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass

  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the name of the wizard and the number of steps.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    return None
#    p = Output.Packet(self, message)
#    if self.Size > 1:
#      speech = '%s, %d steps' % (self.Name, self.Size)
#    else:
#      speech = self.Name
#    p.AddMessage(speech=speech, person=Output.SUMMARY)
#    return p
