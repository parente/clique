'''
Firefox 2

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import re
import UIA, Interface, Config
from protocols import advise
from Chooser import Chooser
from UIA import Adapters
from View import Task, Control

address_path = ['/application[3]/tool bar[4]/tool bar[1]/combo box[5]/editable text[2]', '/application[3]/tool bar[3]/tool bar[1]/combo box[5]/editable text[2]', '/application[3]/tool bar[2]/tool bar[1]/combo box[5]/editable text[2]']

# keeping our bookmarks in the script to overcome MSAA shortcomings in FF2
BM_URLS= ['file:///c:/cygwin/home/parente/studies/final/resources/memory/p1.html',
          'file:///c:/cygwin/home/parente/studies/final/resources/memory/p2.html',
          'file:///c:/cygwin/home/parente/studies/final/resources/memory/p3.html',
          'file:///c:/cygwin/home/parente/studies/final/resources/memory/p4.html',
          'file:///c:/cygwin/home/parente/studies/final/resources/workflow/wiki/index.html']
BM_NAMES = ['First passage', 'Second passage', 'Third passage', 
            'Fourth passage', 'Home, Stu Grey - XYZ Wiki']

class BookmarkAdapter(object):
  advise(instancesProvide=[Interface.IOption])
  def __init__(self, name, url):
    self.name = name
    self.url = url

  def GetName(self):
    return self.name
  
  def GetObject(self):
    return self.url
  
  def GenerateFromLists(cls, names, urls):
    for name, url in zip(names, urls):
      yield BookmarkAdapter(name, url)
  GenerateFromLists = classmethod(GenerateFromLists)

class Main(UIA.Macro):
  # the macro that's run at the very start of the program
  def Sequence(self):
    # watch for firefox
    self.WatchForNewWindow(ClassName='MozillaUIWindowClass', RoleText='window')
    # run firefox
    self.RunFile('c:/program files/mozilla firefox/firefox.exe -P test')
    yield False
    # find the root window
    while self.result.Path != '/':
      self.result = self.result.Parent
    yield True

class DoCreateNewTab(UIA.Macro):
  def Sequence(self):
    # @todo watch for new tab to appear
    # create the new tab
    self.SendKeys('%{f}t')
    #yield False
    yield True

class DoFollowAddress(UIA.Macro):
  def Sequence(self):
    # @todo: change the name on the task to indicate waiting    
    # watch for state change on ROLE_DOCUMENT adding busy
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_STATECHANGE], 
                        Role=UIA.Constants.ROLE_SYSTEM_DOCUMENT, survive=True)
    self.SendKeys('{Enter}')
    yield False
    # check for state busy
    while 1:
      try:
        state = self.result.GetState()
      except Exception:
        yield False
      else:
        yield not (state & UIA.Constants.STATE_SYSTEM_BUSY)
    yield True
    
class DoTypeURLInAddress(UIA.Macro):
  def Sequence(self):
    # check if address bar already has focus
    for ap in address_path:
      c = Interface.IContext(self.task.parent)
      addr = c.GetObjectAt(ap)
      if addr is not None:
        break
    if not (addr.Parent.GetState() & UIA.Constants.STATE_SYSTEM_FOCUSED):
      # watch for focus event
      self.WatchForEvents([UIA.Constants.EVENT_OBJECT_FOCUS], Name='Location',
                          RoleText='combo box')
      # press hotkey to go to address bar
      self.SendKeys('%{d}')
      yield False
    # enter the link text into the bar
    self.SendKeys(self.url)
    # @todo: change the name on the task to indicate waiting
    # watch for state change on ROLE_DOCUMENT adding busy
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_STATECHANGE], 
                        Role=UIA.Constants.ROLE_SYSTEM_DOCUMENT, survive=True)
    self.SendKeys('{Enter}')
    yield False
    # check for state busy
    while 1:
      try:
        state = self.result.GetState()
      except Exception:
        yield False
      else:
        yield not (state & UIA.Constants.STATE_SYSTEM_BUSY)
    yield True

class DoFollowLink(UIA.Macro):
  def Sequence(self):
    # @todo change the name on the task to indicate waiting    
    # watch for state change on ROLE_DOCUMENT adding busy
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_STATECHANGE], 
                        Role=UIA.Constants.ROLE_SYSTEM_DOCUMENT, survive=True)
    self.document.FollowLink()
    yield False
    # check for state busy
    while 1:
      try:
        state = self.result.GetState()
      except Exception:
        yield False
      else:
        yield not (state & UIA.Constants.STATE_SYSTEM_BUSY)
    yield True

class DoNavigateHistory(UIA.Macro):
  def Sequence(self):
    # get direction from instance variable
    if self.direction == 'back':
      # back key
      key = '%{Left}'
    else:
      # forward key
      key = '%{Right}'
      
    # watch for state change on ROLE_DOCUMENT adding busy
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_STATECHANGE], 
                        Role=UIA.Constants.ROLE_SYSTEM_DOCUMENT, survive=True)
    # do key press
    self.SendKeys(key)
    # check for state busy
    while 1:
      try:
        state = self.result.GetState()
      except Exception:
        yield False
      else:
        yield not (state & UIA.Constants.STATE_SYSTEM_BUSY)
    yield True
    
class DoShowAddress(UIA.Macro):
  def Sequence(self):
    # watch for focus event
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_FOCUS], Name='Location:',
                        RoleText='editable text')
    # press hotkey to go to address bar
    self.SendKeys('%{d}')
    yield False
    yield True
    
class BrowseDocument(Task.FormFill):
  Name = 'browse document'
  back_path = ['/application[3]/tool bar[3]/tool bar[1]/push button[0]', 
               '/application[3]/tool bar[2]/tool bar[1]/push button[0]']
  forward_path = ['/application[3]/tool bar[3]/tool bar[1]/push button[1]',
                  '/application[3]/tool bar[2]/tool bar[1]/push button[1]']

  def OnActivate(self, message, auto_focus):
    if message and message.ResultData is not None:
      # some back/foward task ended, update our model
      self.model = message.ResultData
      Interface.IInteractive(self.fields[0].Model).HasChanged()
    return super(BrowseDocument, self).OnActivate(message, auto_focus)
  
  def OnInit(self):
    # add hypertext browsing model and view
    # task model is the document object, so path is always root
    ht = Adapters.HypertextDocument(self, '/')
    document = Control.DocumentReading(self, ht, 'web page', spell=False)
    self.AddField(document)

    # add conditional back/forward tasks
    def GoBackCondition():
      for p in self.back_path:
        c = Interface.IContext(self.parent).GetObjectAt(p)
        if c is not None: break
      try: return not c.IsNotReady()
      except: return False
    def GoForwardCondition():
      for p in self.forward_path:
        c = Interface.IContext(self.parent).GetObjectAt(p)
        if c is not None: break
      try: return not c.IsNotReady()
      except: return False

    # add secondary tasks to the appropriate controls
    document.AddContextOption(GoBack, True, GoBackCondition)
    document.AddContextOption(GoForward, True, GoForwardCondition)

  def OnLoseFocus(self, message):
    self.Name = self.fields[0].Model.GetTitle()

  def OnDoThat(self, message):
    if not message.Press:
      return
    # check if the current document pointer is a link
    doc = Interface.IHypertext(self.fields[0].Model)
    if not doc.IsLink():
      return
    p = self.OutWaiting(message, False)
    self.Output(self, p)
    # stop accepting input
    self.Pause()
    # run the link following macro
    m = DoFollowLink(self, message, self.model, document=doc)
    result = m.Execute()
    # call DoneLink to unpause
    result.AddCallback(self.DoneLink)
    
  def DoneLink(self, result, message):
    '''
    Unpauses this control and plays OutIntroduction on the document

    @param result: Connection object for the last step of the DoFollowLink 
        macro, stored as the new document model
    @type result: pyAA.AccessibleObject
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    self.model = result
    # replace the model of the document view
    ht = Adapters.HypertextDocument(self, '/')
    self.fields[0].Model = ht
    # reintroduce task
    p = self.OutIntroduction(message, False)
    self.Output(self, p) 
    # re-activate hypertext control
    self.ChangeFocus(self.fields[0], message, True)
    # resume accepting keystrokes
    self.Unpause()
  
class GoBack(Task.RunWaitReport):
  Name = 'go back'
  StartMacro = DoNavigateHistory(direction='back')
  Modal = True
  # no successor, just resume the browsing task that started this one and
  # let it update its pointer to the start of the new document

class GoForward(Task.RunWaitReport):
  Name = 'go forward'
  StartMacro = DoNavigateHistory(direction='forward')
  Modal = True

class GoToAddress(Task.FormFill):
  Name = 'go to address'
  StartMacro = DoShowAddress
  CompleteMacro = DoFollowAddress
  Successor = BrowseDocument

class BrowseBookmarks(Task.FormFill):
  Name = 'browse bookmarks'
  StartMacro = DoCreateNewTab
  CompleteMacro = DoTypeURLInAddress
  Successor = BrowseDocument

  def OnInit(self):
    # create a chooser model
    ch = Chooser(BookmarkAdapter.GenerateFromLists(BM_NAMES, BM_URLS))
    # add list view
    lv= Control.List(self, ch, 'bookmarks', label='bookmark')
    self.AddField(lv)
    
  def OnReadyToComplete(self, message):
    # get value from list
    self.ready = False
    # get the selected URL
    url = self.fields[0].Model.GetSelectedItem().GetObject()
    # call completion macro with value provided
    m = self.CompleteMacro(self, message, self.model, url=url)
    result = m.Execute()
    result.AddCallback(self.OnComplete)

Tasks = [BrowseBookmarks] #,GoToAddress
AutoTasks = []
