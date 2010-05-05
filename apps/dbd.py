'''
Day By Day Professional

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import UIA, Output
from UIA import Adapters
from View import Task, Control
from protocols import advise
from Interface import *
import re

NO_EVENTS = 'No notes saved'

class Main(UIA.Macro):
  # the macro that's run at the very start of the program
  def Sequence(self):
    # check if the program is already running
    if self.FindWindow(Name='Day by Day for', ClassName='ThunderRT6FormDC'):
      yield True
    # otherwise start a program instance
    self.WatchForNewWindow(Name='Day by Day for', ClassName='ThunderRT6FormDC')
    self.RunFile('c:\\program files\\day by day professional\\DBDPro.exe')
    yield False
    yield True
    
class DoGotoToday(UIA.Macro):
  def Sequence(self):
    # press the today button
    self.SendKeys('%y')
    yield True
    
class DoDeleteNote(UIA.Macro):
  def Sequence(self):
    # watch for popup menu
    self.WatchForNewWindow(Name='Context', ClassName='#32768')
    # press delete key
    self.SendKeys('%l')
    yield False
    # watch for confirmation window
    self.WatchForNewWindow(Name='Confirm', ClassName='#32770')
    # choose delete current note only
    self.result.SendKeys('{DOWN}{ENTER}')
    yield False
    # choose yes to delete
    self.result.SendKeys('y')
    yield True

class EventsModel(Adapters.EditableList):
  '''
  Overrides Adapters.EditableList to account for the item in the notes list
  stating that there are no notes. Removes the annoying yes/no confirmation on
  note deletion.
  '''
  def GetItemCount(self):
    '''
    Gets a value of zero if the only item in the list is a message saying there
    are no items in the list. Otherwise, returns the number of items.
    
    @return: Number of user created events in the list
    @rtype: integer
    '''
    if self.GetSelectedName() == NO_EVENTS:
      return 0
    else:
      return super(EventsModel, self).GetItemCount()
    
class EventsView(Control.List):
  '''
  Overrides the Control.List to account for the complex sequence of commands
  needed to delete a single note.
  '''
  def OnDelete(self, message):
    '''
    Deletes the currently selected note. Runs the DoDeleteNote macro when the 
    delete command is given to simplify deletion to a single key press. Pauses 
    this control so it will not process user input while the macro is running.
    Sets DoneDelete to receive a callback when the Macro is complete.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if IFiniteCollection(self.model).GetItemCount() == 0:
      p = self.OutNotImplemented(message, 'No note to delete.')
      self.Output(self, p)
      return
    # stop accepting input
    self.Pause()
    # run the deletion macro
    print self.model
    print self.model.subject
    m = DoDeleteNote(self, message, self.model.subject)
    result = m.Execute()
    # call DoneDelete to unpause and do OutDelete when complete
    result.AddCallback(self.DoneDelete)    
    
  def DoneDelete(self, result, message):
    '''
    Unpauses this control and plays OutDelete.

    @param result: Connection object for the last step of the DoDeleteNote 
        macro, unused
    @type result: pyAA.AccessibleObject
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    self.Unpause()
    p = self.OutDeleteItem(message)
    self.Output(self, p)
    
class CalendarList(Control.StridedList):
  '''
  Improves the output of dates to account for the current navigation stride. For
  instance, if the user is browsing by day, the date is read as given as day of
  the week, month, day, year. If the user is browsing by week, the date is read
  as month, day, year, day of the week. If the user is browsing by month, the
  date is read as month, day of the week, day, year. If the user is browsing by 
  year the date is read as year, day of week, month, day.
  '''
  def OutCurrentItem(self, message):
    '''
    Outputs the current date formatted appropriately to the current stride 
    level.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IStrideable(self.model)
    level = m.GetLevel()
    p = Output.Packet(self, message)
    # never empty, so no default needed
    text = m.GetSelectedName()
    chunks = text.split(' ')
    # get rid of the star marker
    if chunks[0] == '*': chunks.pop(0)
    if level == 'Day':
      text = ' '.join(chunks)
    if level in ('Week', 'Month'):
      text = ' '.join([chunks[1], chunks[2], chunks[3], chunks[0]])
    elif level == 'Year':
      text = ' '.join([chunks[3], chunks[0], chunks[1], chunks[2]])
    p.AddMessage(speech=text, person=Output.CONTENT)
    return p

class CalendarModel(object):
  '''
  Wraps multiple components of the application interface for use through the
  L{Control.StridedList}. Provides IInteractive, IInfiniteCollection, and 
  IStrideable interfaces.
  
  @cvar prev_path: Path to the Previous button
  @type prev_path: string
  @cvar next_path: Path to the Next button
  @type next_path: string
  @cvar stride_path: Path to the drop down list for selecting the current stride
  @type stride_path: string
  @cvar date_path: Path to the text box displaying the selected date
  @type date_path: string
  @ivar context: Context in which the control is located
  @type: L{Interface.IContext}
  '''
  advise(instancesProvide=[IInteractive, IInfiniteCollection, IStrideable])
  prev_path = '/client[3]/window[5]/push button[3]'
  next_path = '/client[3]/window[3]/push button[3]'
  stride_path = '/client[3]/window[7]/combo box[3]'
  date_path = '/client[3]/window[10]/editable text[3]'
  
  def __init__(self, context):
    '''
    Stores a reference to the context which contains the objects forming the
    calendar.
    
    @param context: Context in which the control is located
    @type: L{Interface.IContext}
    '''
    self.context = context

  def Activate(self):
    '''
    Queries the context for the controls forming this interaction pattern.
    
    @return: Were the objects activated properly?
    @type: boolean
    '''
    self.date = Adapters.TextBox(self.context, self.date_path)
    self.stride = Adapters.DropDownList(self.context, self.stride_path)
    self.next = IContext(self.context).GetObjectAt(self.next_path)
    self.prev = IContext(self.context).GetObjectAt(self.prev_path)
    self.date.Activate()
    self.stride.Activate()
    self.stride.Deactivate()
    return True
    
  def Deactivate(self):
    '''Does nothing.'''
    pass
  
  def GetName(self, override, default='calendar date'):
    '''
    Gets the name for this object. Returns the L{View} specified name override
    if it is given else returns the default.
    
    @param override: Name specified by the L{View}
    @type override: string
    @param default: Default name for the L{View}
    @type default: string
    @return: Name of this model
    @rtype: string
    '''
    if override:
      return override
    else:
      return default
  
  def HasChanged(self):
    '''
    Always returns false since the calendar is never changed indirectly.
    
    @return: False
    @rtype: boolean
    '''
    return False
  
  def GetSelectedName(self, default=''):
    '''
    Gets the current date.
    
    @param default: Name to return if nothing is selected
    @type default: string
    @return: Selected name
    @rtype: string
    '''
    self.date.UpdateChunks()
    return self.date.GetAllText()
  
  def NextItem(self): 
    '''
    Selects the next item using the current stride.
    
    @return: Always False, selection cannot wrap
    @rtype: boolean
    '''
    self.next.DoDefaultAction()
    return False
    
  def PrevItem(self):
    '''
    Selects the previous item using the current stride.
    
    @return: Always False, selection cannot wrap
    @rtype: boolean
    '''
    self.prev.DoDefaultAction()
    return False
   
  def GetLevel(self):
    '''
    Gets the name of the current stride.
    
    @return: Name of the stride level
    @rtype: string
    '''
    return self.stride.GetSelectedName()
    
  def PrevLevel(self):
    '''
    Chooses the next larger stride level if it exists.
    
    @return: Was the next larger stride level selected?
    @rtype: boolean
    '''
    if self.stride.GetIndex() == self.stride.GetItemCount()-1:
      rv = False
    else:
      self.stride.NextItem()
      rv = True
    return rv
      
  def NextLevel(self):
    '''
    Chooses the next smaller stride level if it exists.
    
    @return: Was the next smaller stride level selected?
    @rtype: boolean
    '''
    if self.stride.GetIndex() == 0:
      rv = False
    else:
      self.stride.PrevItem()
      rv = True      
    return rv
    
class GotoToday(Task.RunAndReport):
  Name = 'go to today'
  StartMacro = DoGotoToday

class GotoDate(Task.FormFill):
  Modal = True
  Name = 'go to a specific date'
  text_path = '/dialog[3]/window[1]/editable text[3]'
  date_regex = re.compile('\d{2}/\d{2}/\d{4}')
  date_text = 'date in two digit day slash two digit month slash four digit year format'
  StartMacro = UIA.StartWindowByKey(Name='Move to date',
                                    ClassName='#32770', 
                                    key_combo='^m')
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  CancelMacro = UIA.EndWindowByButton()
  
  def IsValid(self):
    if self.date_regex.search(self.textbox.GetAllText()) is not None:
      return None
    else:
      return 'You must enter a ' + self.date_text
      
  def OnInit(self):
    # date entry text box
    self.textbox = Adapters.EditableTextBox(self, self.text_path, 
                                            multiline=False)
    self.AddField(Control.TextEntry(self, self.textbox, self.date_text, 
                                    spell=True))
  
class CreateNote(Task.FormFill):
  Modal = True
  Name = 'create new note'
  text_path = '/client[3]/window[2]/editable text[3]'
  StartMacro = UIA.StartWindowByKey(Name='Attach Note', 
                                    ClassName='ThunderRT6FormDC', 
                                    key_combo='%t')
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  CancelMacro = UIA.EndWindowByButton()
  
  def IsValid(self):
    if self.textbox.GetAllText() != '':
      return None
    else:
      return 'You must enter some text into the note.'
  
  def OnInit(self):
    # note text box
    self.textbox = Adapters.EditableTextBox(self, self.text_path, 
                                            multiline=False)
    self.AddField(Control.TextEntry(self, self.textbox, 'note description', 
                                    spell=True))
    
class EditNote(CreateNote):
  Name = 'edit current note'
  StartMacro = UIA.StartWindowByKey(Name='Edit Note', 
                                    ClassName='ThunderRT6FormDC', 
                                    key_combo='^e')
  
class SearchStringStep(Task.FormFill):
  Name = 'enter search string'
  text_path = '/dialog[3]/window[1]/editable text[3]'
  StartMacro = UIA.StartWindowByKey(key_combo='%i', ClassName='#32770',
                                    Name='Find')
  CancelMacro = UIA.EndWindowByButton()

  def OnInit(self):
    # search string text box
    self.textbox = Adapters.OverwritableTextBox(self, self.text_path, 
                                            multiline=False)
    self.AddField(Control.TextEntry(self, self.textbox, spell=True))
    
  def IsValid(self):
    if self.textbox.GetAllText() != '':
      return None
    else:
      return 'You must enter some text as the search string.'

class SearchResultsStep(Task.LinkedBrowsing):
  Name = 'choose a search result'
  date_path = '/client[3]/window[3]/list[3]'
  description_path = '/client[3]/window[2]/list[3]'
  StartMacro = UIA.StartWindowByKey(key_combo='{ENTER}', Name='Search Results',
                                    ClassName='ThunderRT6FormDC')
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  CancelMacro = UIA.EndWindowByButton()
  
  def OnInit(self):
    date_list = Adapters.List(self, self.date_path, select_hack=True)
    desc_list = Adapters.List(self, self.description_path)
    self.AddView(Control.List(self, date_list, 'search result dates', 'date'))
    self.AddView(Control.List(self, desc_list, 'search result notes', 'note'))
  
class SearchCalendar(Task.Wizard):
  Name = 'search calendar'
  Modal = True
  
  def OnInit(self):
    self.AddStep(SearchStringStep)
    self.AddStep(SearchResultsStep)

class BrowseCalendar(Task.LinkedBrowsing):
  Name = 'browse calendar'
  Permanence = Task.NO_START|Task.NO_END
  notes_path = '/client[3]/window[9]/list[3]'
  description_path = '/client[3]/window[8]/editable text[3]'
  
  def OnInit(self):
    tr = CalendarModel(self)
    el = EventsModel(self, self.notes_path, select_hack=True)
    tb = Adapters.TextBox(self, self.description_path)
    
    # create and add views in order of influence
    calendar = CalendarList(self, tr, 'dates', label='')
    events = EventsView(self, el, 'notes', label='note')
    description = Control.TextReading(self, tb, 'note description')
    self.AddView(calendar)
    self.AddView(events)
    self.AddView(description)
    
    def EditNoteCondition():
      m = events.Model
      return m.GetSelectedName() != NO_EVENTS
    
    # add context sensitive options
    self.AddContextOption(CreateNote, True)
    events.AddContextOption(EditNote, True, EditNoteCondition)
    description.AddContextOption(EditNote, True, EditNoteCondition)
    self.AddContextOption(GotoToday, True)
    self.AddContextOption(GotoDate, True)
    self.AddContextOption(SearchCalendar, True)
    
class AutoNoSearchResults(Task.RunWaitReport):
  Modal = True
  Name = 'no search results found'
  Permanence = Task.Constants.NO_COMPLETE
  CancelMacro = UIA.WaitEndWindowByKey(key_combo='{ENTER}')
  
  def OutWaiting(self, message, auto_focus):
    p1, p2 = super(AutoNoSearchResults, self).OutWaiting(message, auto_focus)
    p2.UpdateMessage(Output.SUMMARY, listen=True)
    return (p1, p2)
  
  def OnSayDone(self, message):
    self.CancelMacro.Continue()
   
  def Trigger(cls, event, model, container):
    return not (model.State & UIA.Constants.STATE_SYSTEM_SIZEABLE) and \
           model.Name == 'Message' and model.ClassName == '#32770'
  Trigger = classmethod(Trigger)    
    
Tasks = [BrowseCalendar]
AutoTasks = [AutoNoSearchResults]
