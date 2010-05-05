'''
Defines containers for starting and managing tasks.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from protocols import advise
import Interface
import Chooser
import Output
import Input
import Base, Constants
import Loader, Support, System, UIA
import View
import weakref

# clean watchers every two minutes
STABILITY_CLEAN_DELAY = 120

class ProgramOptionAdapter(object):
  '''
  Wraps a L{Program} instance or a L{Program} class in the L{Interface.IObject}
  interface. This allows the program to be listed as an option by a L{Chooser}.
  
  @ivar subject: Program option to be listed by the chooser
  @type subject: L{Program} instance or class
  '''
  advise(instancesProvide=[Interface.IOption])
  def __init__(self, subject):
    '''
    Stores the subject.
    
    @param subject: Program option to be listed by the chooser
    @type subject: L{Program} instance or class
    '''
    self.subject = subject
    
  def GetName(self):
    '''
    @return: Name of the L{Program}
    @rtype: string
    '''
    return self.subject.Name
  
  def GetObject(self):
    '''
    @return: L{Program} or other L{View.Task} represented by this option
    @rtype: L{View.Base} class or instance
    '''
    return self.subject
  
  def GenerateFromList(cls, subjects):
    '''
    Generates a single L{ProgramOptionAdapter} for each subject in subjects on
    each invocation. A convenience class method.
    
    @param subjects: List of objects adaptable to L{IOption} by this class
    @type subjects: list
    '''
    for subject in subjects:
      yield ProgramOptionAdapter(subject)
  GenerateFromList = classmethod(GenerateFromList)
  
class TaskOptionAdapter(ProgramOptionAdapter):
  '''
  Wraps a L{View.Task.Base} instance or class in the L{Interface.IObject}
  interface. This allows a task to be listed as an option by a L{Chooser}.
  
  @ivar subject: Task option to be listed by the chooser
  @type subject: L{View.Task.Base} instance or class
  @ivar owner: Object that owns the subject
  @type owner: L{View.Base}
  '''
  def __init__(self, subject, owner):
    '''
    Stores the subject and its owner.
    
    @param subject: Task option to be listed by the chooser
    @type subject: L{View.Task.Base} instance or class
    @param owner: Object that owns the subject
    @type owner: L{View.Base}
    '''
    super(TaskOptionAdapter, self).__init__(subject)
    self.owner = owner
  
  def GetOwner(self):
    '''
    @return: Object that owns the subject
    @rtype: L{View.Base}
    '''
    return self.owner
  
  def GenerateFromList(cls, subjects, owners):
    '''
    Generates a single L{TaskOptionAdapter} for each subject in subjects on each
    invocation. A convenience class method.
    
    @param subjects: List of objects adaptable to L{IOption} by this class
    @type subjects: list
    '''
    for i in xrange(len(subjects)):
      yield TaskOptionAdapter(subjects[i], owners[i])
  GenerateFromList = classmethod(GenerateFromList)

class ProgramManager(Base.Task):
  '''
  Manages all programs in the system. Implements the Singleton pattern.
  
  @cvar instance: Singleton instance
  @type instance: L{Manager}
  @ivar stability_watchers: Stability monitors indexed by process ID
  @type stability_watchers: dictionary
  @ivar last_focus: Last non-chooser object to have the focus
  @type last_focus: object
  @param programs: Instantiated programs
  @type programs: list
  '''
  instance = None
  Permanence = Constants.NO_START
  
  def __new__(cls, parent=None):
    '''
    Initializes a single instance of a class and store it in a class variable. 
    Returns that instance whenever this method is called again. Implements the 
    Singleton design pattern.
    
    @param parent: Parent object in the output pipeline
    @type parent: L{Output.Mananger.Pipe}
    @return: Instance of this class
    @rtype: L{Manager}
    '''
    # return an existing instance
    if cls.instance is not None:
      return cls.instance
    
    # build and initialize a new instance
    self = Base.Task.__new__(cls)
    super(cls, self).__init__(parent, None)
    # attach to the input pipeline, just below the output manager
    self.parent.FocusNow(self)
    # store references to running programs
    self.programs = []
    # store stability watchers
    self.stability_watchers = {}
    # focus before the menu is displayed
    self.last_focus = None
    # register future to clean up stability watchers
    System.Pump().RegisterFuture(STABILITY_CLEAN_DELAY, 
                                 self.FreeStabilityWatchers)
    # store the instance for later
    cls.instance = self
    return self
    
  def __init__(self, *args, **kwargs): pass
  
  def IsMenuActive(self):
    '''
    @return: Is the list of tasks the focus?
    @rtype: boolean
    '''
    return isinstance(self.focus, View.Control.List)
  
  def FreeStabilityWatchers(self):
    '''
    Cleans up stability watchers for dead processes. This method is registered 
    with the main message pump to be called on a set schedule.
    '''
    alive = Support.GetPIDs()
    for key in self.stability_watchers.keys():
      try:
        alive[key]
      except KeyError:
        w = self.stability_watchers[key]
        w.Destroy()
        del self.stability_watchers[key]
        # inform programs that the process died
        for p in self.programs:
          p.RemoveAutoTasks(key)
    # re-register future
    System.Pump().RegisterFuture(STABILITY_CLEAN_DELAY, 
                                 self.FreeStabilityWatchers)
    
  def GetStabilityWatcher(self, pid):
    '''
    Retrieves the stability watcher for the given process or creates a new one.
    
    @param pid: Process id
    @type pid: integer
    @return: Stability watcher for the given process id
    @rtype: L{UIA.Watcher.StabilityWatcher}
    '''
    if pid > 0xffff: return None
    try:
      return self.stability_watchers[pid]
    except KeyError:
      # notify the active program about the new process
      if not self.IsMenuActive() and self.focus is not None:
        self.focus.AddAutoTasks(pid)
      sw = UIA.StabilityWatcher(pid)
      self.stability_watchers[pid] = sw
      return sw
    
  def Output(self, source, packets):
    '''
    Passes audio output to the output manager. If the program sending the output 
    information is not in focus, demote the output to the inactive speaker.
    
    @param source: Object that called this output method
    @type source: L{Output.Manager.Pipe}
    @param packets: Packets to output
    @type packets: tuple or single L{Output.Messages.OutboundPacket}
    '''
    try:
      len(packets)
    except:
      packets = (packets,)    
    for packet in packets:
      if packet and source != self.focus and source != self:
        packet.RouteTo(Output.INACTIVE_PROG)
    self.parent.Output(self, packets)
    
  def StartObject(self, message, factory):
    '''
    Start a new program by loading its pattern description from disk, 
    initializing it, and focusing on it.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param factory: Callable that will create the program adapter
    @type factory: L{Loader.Stub}
    '''
    # create the pattern description
    adapter = factory()
    p = Program(self, factory.Name, adapter)
    # add the program to the list of running programs
    self.programs.append(p)
    self.programs.sort()
    # switch the focus to the new program immediately
    self.ChangeFocus(p, message, False)
    # let the program initialize itself
    p.OnInit()
    p.OnStart(message)
    
  def OnActivate(self, message, auto_focus):
    '''    
    Reactivates the L{Task} with the focus or starts the program chooser if
    there is no focus. Always introduces the chooser whether it was running
    previously or not.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    '''
    if super(ProgramManager, self).OnActivate(message, auto_focus):
      try:
        # if the menu is active, output choose task
        if self.IsMenuActive():
          p = self.OutChooseProgram(self)
          self.Output(self, p)
        # resume the focused program or chooser
        self.focus.OnActivate(message, auto_focus)
      except AttributeError:
        # create a main program chooser
        message.Seen = False
        self.OnChooseProgram(message, auto_focus)
      return True
    else:
      return False
    
  def OnSystemStartup(self, message):
    '''
    Handle a request to start interaction by presenting the dead program list.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    self.OnChooseProgram(message)
    
  def OnChooseProgram(self, message):
    '''
    Lists all the support programs. Lets the user choose one to activate.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # don't nest menus
    if self.IsMenuActive(): return

    # combine started and unstarted programs
    stubs = Loader.Library.GetStubs()
    all = dict([(s.Name, s) for s in stubs])
    running = dict([(p.Name, p) for p in self.programs])
    all.update(running)
    options = all.values()
    options.sort()

    # announce the chooser
    p = self.OutChooseProgram(self)
    self.Output(self, p)
    # create a list with the program menu as model
    menu = ProgramOptionAdapter.GenerateFromList(options)
    chooser = Chooser.Chooser(menu)
    #Interface.IInteractive(self.model).Activate()
    plist = View.Control.List(self, chooser, name='program menu', label='program')
    #self.OnActivate(message, False)
    self.last_focus = self.focus
    self.ChangeFocus(plist, message, False)
    
  def OnReadyToComplete(self, message):
    '''
    Switch to a running program or start a new one.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if not self.IsMenuActive(): return
    # query the list for the active item
    option = self.focus.Model.GetSelectedItem()
    try:
      # switch to a running program
      self.ChangeFocus(option.GetObject(), message, False)
    except NotImplementedError:
      # start a new program
      self.StartObject(message, option.GetObject())
    self.last_focus = None
    
  def OnReadyToCancel(self, message):
    '''
    Cancel a choose operation.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.last_focus:
      # auto focus is false because there is no cancel sound
      self.ChangeFocus(self.last_focus, message, False)
      self.last_focus = None
    
  def OnChooseTask(self, message):
    '''
    Reports that the main options for a program are not currently available.
    
    Calls OutRefuseTask.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.IsMenuActive():
      p = self.OutRefuseTask(message)
    else:
      p = self.OutNoTasks(message)
    self.Output(self, p)
    
  def OutChooseProgram(self, message):
    '''
    Plays the program chooser identity sound and introduction if no other
    context change sound is playing.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Packet of information to be output
    @rtype: tuple of L{Output.Messages.OutboundPacket}
    '''
    # silence any program ambience and start the main menu loop
    p = Output.Packet(self, message, Output.CONTEXT)
    p.AddMessage(sound=Output.ISound(self).Action('start'))
    p.AddMessage(sound=Output.ISound(self).Identity('task'),
                 person=Output.LOOPING)
    p.AddMessage(sound=None, person=Output.AMBIENCE)
    return p
  
  def OutIntroduction(self, message, auto_focus):
    '''
    Do nothing.
    '''
    return None
    
  def OutWhereAmI(self, message):
    '''
    Plays the end of the where am I report sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = View.Base.OutWhereAmI(self, message)
    p.AddMessage(sound=Output.ISound(self).State('last'), 
                 person=Output.SUMMARY)
    return p
    
  def OutRefuseTask(self, message):
    '''
    Outputs the refuse sound and a message explaining that the user must 
    choose a program before accessing the task menu.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(speech='You must choose a program before choosing a task.', 
                 person=Output.SUMMARY, 
                 sound=Output.ISound(self).Warn('refuse'))
    return p
    
  def OutNoTasks(self, message):
    '''
    Outputs the refuse sound and a message explaining that there are no
    tasks to start here.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(speech='There are no tasks to start or resume here.', 
                 person=Output.SUMMARY, 
                 sound=Output.ISound(self).Warn('refuse'))
    return p
  
class Program(Base.Task):
  '''
  Represents a single running application. Manages tasks within that application.
  
  @ivar Name: Name of the program
  @type Name: string
  @ivar last_focus: Last non-chooser object to have the focus
  @type last_focus: object
  @ivar adapter: Pattern description for this application
  @type adapter: module
  @ivar tasks: Running tasks
  @type tasks: list of L{Task.Base.Task}
  @ivar owners: Owners of running tasks
  @type owners: list
  @ivar conditions: Conditions under which the autotasks for this program are
    registered keyed by process ID
  @type conditions: dictionary
  '''
  def __init__(self, parent, name, adapter):
    '''
    Initializes the program by storing the program manager reference, name of 
    the program, and the adapter file containing its task definitions.

    See instance variables for parameter descriptions.
    '''
    super(Program, self).__init__(parent, None)
    self.Name = name
    self.adapter = adapter
    self.tasks = []
    self.owners = []
    self.conditions = {}
    try:
      self.StartMacro = self.adapter.Main
    except AttributeError:
      pass
    
  def GetContainer(self):
    '''
    Returns itself as the most parent container of a task.
    
    @return: This instance
    @rtype: L{Program}
    '''
    return self
  
  def GetTask(self, index):
    '''
    Gets the task at the given index in the task list.
    
    @param index: Index in the tasks list
    @type index: integer
    @return: Task at index or None
    @rtype: L{Base.Task}
    '''
    try:
      return self.tasks[index]
    except IndexError:
      return None
      
  def IsMenuActive(self):
    '''
    @return: Is the list of tasks the focus?
    @rtype: boolean
    '''
    return isinstance(self.focus, View.Control.List)
  
  def AddAutoTasks(self, pid):
    '''
    Registers all auto tasks for this program on the new process ID.
    
    @param pid: Process ID
    @type pid: integer
    '''
    for task in self.adapter.AutoTasks:
      c = UIA.EventManager.addCondition(UIA.Constants.EVENT_OBJECT_SHOW,
                                        task.Trigger, pid=pid, front=False,
                                        container=weakref.proxy(self))
      c.setListener(self.StartAutoTask, task)
      self.conditions.setdefault(pid, []).append(c)
  
  def RemoveAutoTasks(self, pid):
    '''
    Unregisters all auto tasks for this program from the new process ID.
    
    @param pid: Process ID
    @type pid: integer
    '''
    try:
      conditions = self.conditions[pid]
      del self.conditions[pid]
    except KeyError:
      return
    for c in conditions:
      UIA.EventManager.removeCondition(c)
      
  def StartAutoTask(self, model, factory):
    '''
    Starts an auto task when triggered. Calls L{StartObject} providing the 
    necessary information.

    @param model: Starting model for the L{Task}
    @type model: pyAA.AccessibleObject
    @param factory: Callable that will create the new task
    @type factory: class
    '''
    if self.IsMenuActive() or self.focus is None:
      owner = self
    else:
      owner = self.focus
    # make a fake message so we interrupt
    message = Input.Messages.InboundMessage(None)
    try:
      owner.StartObject(message, factory, model)
    except (AttributeError, TypeError):
      self.StartObject(message, factory, model, owner)
      
  def StartObject(self, message, factory, model, owner, focus=True):
    '''
    Start a new task in this program. 
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param factory: Callable that will create the new task
    @type factory: class
    @param model: Context model for the object
    @type model: pyAA.AccessibleObject
    @param owner: Task that will receive the focus when the task dies
    @type owner: L{View.Task.Base.Task}
    @param focus: Should the task receive the focus immediately?
    @type focus: boolean
    @return: Started object
    @rtype: L{View.Base}
    '''
    # create the task object
    t = factory(self, model)
    # save the task and its owner
    self.tasks.append(t)
    self.owners.append(owner)
    # let the task initialize itself
    t.OnInit()
    # switch the focus to the new task immediately
    if focus: self.ChangeFocus(t, message, True)
    t.OnStart(message)
    return t
    
  def EndObject(self, message, task, model, completed):
    '''
    End a task running in this program.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param task: Task to end
    @type task: L{Task.Base.Task}
    @param model: Context model for the object
    @type model: L{Interface.IContext}
    @param completed: Did the task complete (True) or was it canceled (False)?
    @type completed: boolean
    '''
    task.Shutdown()
    # get rid of the task object
    i = self.tasks.index(task)
    self.tasks.pop(i)
    # get the owner of the ending task
    owner = self.owners.pop(i)
    if (task.Successor is not None) and completed:
      # the ending task has a successor, start it
      self.StartObject(None, task.Successor, model, owner)
    elif owner is self:
      # the program is the owner, start the main menu
      message.Seen = False
      self.ChangeFocus(None, message, False)
      # auto focus is true to allow cancel sound to play for object
      self.OnActivate(message, True)
    else:
      # provide the result data
      message.ResultData = model
      # another task is the owner, resume it
      self.ChangeFocus(owner, message, True)
    
  def OnActivate(self, message, auto_focus):
    '''
    Reactivates the L{Task} with the focus or starts the task chooser if there
    is no focus. Always introduces the chooser whether it was running
    previously or not.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    '''
    if super(Program, self).OnActivate(message, auto_focus):
      try:
        # if the menu is active, output choose task
        if self.IsMenuActive():
          p = self.OutChooseTask(self, auto_focus)
          self.Output(self, p)
        # resume the focused task
        self.focus.OnActivate(message, auto_focus)
      except AttributeError:
        # create a main task chooser
        message.Seen = False
        self.OnChooseTask(message, auto_focus)
      return True
    else:
      return False

  def OnReadyToUse(self, message):
    '''
    Starts any permanent tasks once the model has been established. Registers 
    any auto tasks with PIDs already associated with this program.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}    
    @param model: 
    @type model: 
    '''
    for i in range(len(self.adapter.Tasks)):
      t = self.adapter.Tasks[i]
      if hasattr(t, 'Permanence') and (t.Permanence & Constants.NO_START):
        t = self.StartObject(message, t, self.model, self, focus=False)
        # autostart this task if it is the only one
        if len(self.adapter.Tasks) == 1:
          self.focus = t
    # remove the permanents
    i = 0
    while i < len(self.adapter.Tasks):
      t = self.adapter.Tasks[i]
      if hasattr(t, 'Permanence') and (t.Permanence & Constants.NO_START):
        del self.adapter.Tasks[i]
      else: i += 1
      
  def OnReadyToComplete(self, message):
    '''
    Switch to a running program or start a new one.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # query the list for the active item
    option = self.focus.Model.GetSelectedItem()
    try:
      # switch to a running task
      self.ChangeFocus(option.GetObject(), message, False)
    except NotImplementedError:
      # start a new task
      owner = option.GetOwner()
      self.StartObject(message, option.GetObject(), owner.Model, owner)
    self.last_focus = None
    
  def OnReadyToCancel(self, message):
    '''
    Cancel a choose operation.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.last_focus:
      # auto focus is False to play resume sound
      self.ChangeFocus(self.last_focus, message, False)
      self.last_focus = None
      
  def EvalPreconditions(self, options, source):
    '''
    Validate preconditions to determine what tasks are available to start.
    
    @param options: L{Support.Bag}s of Condition, Class, and Owned
    @type options: list
    @param source: Object that should own tasks that want to be owned
    @type source: L{View.Base}
    @return: Menu of available options
    @rtype: L{Chooser.Options}
    '''
    # validate preconditions
    evaled = {}
    opts = []
    owners = []
    for o in options:
      try: 
        # look up a condition in the cache
        available = evaled[id(o.Condition)]
      except KeyError: 
        # evaluate the condition
        available = o.Condition()
        evaled[id(o.Condition)] = available
      except AttributeError:
        # a task that's always available
        opts.append(o)
        owners.append(self)
        continue
        
      # only allow options that are available
      if available:
        # determine the owner of the source
        if o.Owned:
          opts.append(o.Class)
          owners.append(source)
        else:
          opts.append(o.Class)
          owners.append(self)  
       
    if not len(opts):
      # return None if there are no options to list
      return None
    else:
      # else return an option generator
      return TaskOptionAdapter.GenerateFromList(opts, owners)

  def OnChooseTask(self, message, auto_focus=False):
    '''
    Lists all the tasks that can be started or resumed here. Lets the user
    choose one. Evaluates preconditions for task availability.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    '''    
    # don't nest menus
    if self.IsMenuActive(): return
    
    try:
      # do not start a task if the current task is modal
      if self.focus.Modal:
        p = self.OutNoSwitch(message)
        self.Output(self, p)
        return
    except AttributeError:
      pass
      
    # combine options
    if message.Seen:
      options = self.adapter.Tasks + self.tasks + message.UserData.Options
      source = message.UserData.Source
    else:
      options = self.adapter.Tasks + self.tasks
      source = self
      
    # evaluate preconditions
    menu = self.EvalPreconditions(options, source)
        
    # quit early if there are no options, but allow to propogate
    if menu is None:
      message.Stop = False
      message.UserData = None
      return
    
    # announce the chooser
    p = self.OutChooseTask(self, auto_focus)
    self.Output(self, p)
    # activate the model and show the menu
    #Interface.IInteractive(self.model).Activate()   
    chooser = Chooser.Chooser(menu)
    tlist = View.Control.List(self, chooser, name='task menu', label='task')
    self.last_focus = self.focus
    self.ChangeFocus(tlist, message, False)
    
  def OutIntroduction(self, message, auto_focus):
    '''
    Plays the program identity sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Packet of information to be output
    @rtype: tuple of L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.CONTEXT)
    # play the program ambience
    p.AddMessage(sound=Output.ISound(self).Identity('container'),
                 person=Output.AMBIENCE)
    return p
    
  def OutChooseTask(self, message, auto_focus):
    '''
    Plays the task chooser identity sound and introduction if no other
    context change sound is playing.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Packet of information to be output
    @rtype: tuple of L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.CONTEXT)
    # only play the start sound if something else isn't playing
    if not auto_focus:
      p.AddMessage(sound=Output.ISound(self).Action('start'))
    # play the task chooser sound
    p.AddMessage(sound=Output.ISound(self).Identity('task'),
                 person=Output.LOOPING)
    return p
    
  def OutWhereAmI(self, message):
    '''
    Outputs the name of the program.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = super(Base.Task, self).OutWhereAmI(message)
    s = 'in the %s program' % self.Name
    p.AddMessage(speech=s, person=Output.SUMMARY)
    return p
        
  def OutNoSwitch(self, message):
    '''
    Outputs the refuse sound and a message stating that this task must be 
    completed before the user can switch to another task.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).Warn('refuse'),
                 person=Output.SUMMARY,
                 speech='You must finish this task before choosing another.')
    return p
