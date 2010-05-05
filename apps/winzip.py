'''
Winzip 11

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import UIA, Interface, Output
from UIA import Adapters
from View import Task, Control

class Main(UIA.Macro):
  # do nothing on program start
  pass
    
class DoStartNewWindow(UIA.Macro):
  # create a new winzip instance
  def Sequence(self):
    self.WatchForNewWindow(Name='WinZip', ClassName='WinZipWClass', name='main')
    self.WatchForNewDialog(Name='WinZip', name='eval')
    self.RunFile('winzip.exe')
    yield False
    if self.name != 'main':
      for key in ['e', 'v']:
        # if the popup comes up, try alt-e or alt-v
        self.WatchForNewWindow(Name='WinZip', ClassName='WinZipWClass', name='main')
        self.WatchForNewDialog(Name='WinZip', name='eval')
        self.result.SendKeys('%%{%s}' % key)
        yield False
        if self.name == 'main': break
        self.result.SendKeys('{ENTER}')
    yield True
    
class DoEndCreateArchiveWithoutAdd(UIA.Macro):
  # deselect the add checkbox and close the file dialog
  def Sequence(self):
    cond = lambda x: x.Role == UIA.Constants.ROLE_SYSTEM_CHECKBUTTON and \
                     x.Name == 'Add dialog'
    check = self.model.FindOneChild(cond)
    if check.State & UIA.Constants.STATE_SYSTEM_CHECKED:
      check.DoDefaultAction()
    # watch for the add window
    self.WatchForWindowClose(self.model.Window)
    self.SendKeys('{ENTER}')
    yield False
    yield True
    
class DoSelectAllThenExtract(UIA.Macro):
  # select all files before extracting
  def Sequence(self):
    # select all files in archive
    self.SendKeys('^{a}')
    self.WatchForNewWindow(Name='Extract', ClassName='#32770')
    self.model.SendKeys('+{e}')
    yield False
    yield True
    
class DoWatchExtractProgress(UIA.Macro):
  # progress bar appears at /client[3]/window[0]/status bar[3]/window[4]/progress bar[3]
  def Sequence(self):
    # watch the status bar for the summary event
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_NAMECHANGE], Name='Total')
    # close the extract window
    self.SendKeys('%{e}')
    yield False
    yield True
    
class DoWatchAddProgress(UIA.Macro):
  ok_button = '/dialog[3]/window[0]/push button[3]'
  no_button = '/dialog[3]/window[1]/push button[3]'
  def Sequence(self):
    # watch for the appearance of the nothing to do dialog
    self.WatchForNewDialog(Name='Winzip', name='nothing')
    # watch the status bar for the summary event
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_NAMECHANGE], name='done',
                        Name='Total')
    # close the window
    self.SendKeys(self.key_combo)
    yield False
    if self.name == 'nothing':
      # watch for the review error log dialog
      self.WatchForNewDialog(Name='Winzip')
      # close the nothing to do dialog
      b = self.result.ChildFromPath(self.ok_button)
      b.DoDefaultAction()
      yield False
    else:
      # the add operation completed, so end
      yield True
    # watch for review error dialog close
    self.WatchForWindowClose(self.result.Window)
    # close the nothing to do dialog
    b = self.result.ChildFromPath(self.no_button)
    b.DoDefaultAction()
    yield False
    # the nothing to do dialog died, so end
    yield True
    
class DoDeleteFile(UIA.Macro):
  def Sequence(self):
    # watch for popup menu
    self.WatchForNewWindow(Name='Delete', ClassName='#32770')
    # press delete key
    self.SendKeys('{DEL}')
    yield False
    # watch the status bar for the summary event
    self.WatchForEvents([UIA.Constants.EVENT_OBJECT_NAMECHANGE], Name='Total')
    #self.WatchForWindowClose(self.result.Window)
    # choose delete selected file only
    self.SendKeys('{s}{ENTER}')
    yield False
    yield True
    
class FileView(Control.List):
  '''
  Overrides the Control.List to account for the complex sequence of commands
  needed to delete a single file.
  '''
  def OnDelete(self, message):
    '''
    Deletes the currently selected file. Runs the DoDeleteFile macro when the 
    delete command is given to simplify deletion to a single key press. Pauses 
    this control so it will not process user input while the macro is running.
    Sets DoneDelete to receive a callback when the Macro is complete.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # stop accepting input
    self.Pause()
    # run the deletion macro
    m = DoDeleteFile(self.parent, message, self.model.subject)
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
    # select the first item
    Interface.IFiniteCollection(self.model).FirstItem()
    p = self.OutDeleteItem(message)
    self.Output(self, p)
    
class WaitWhileExtracting(Task.RunWaitReport):
  Name = 'extracting, please wait'
  StartMacro = DoWatchExtractProgress
  
class WaitWhileAdding(Task.RunWaitReport):
  Name = 'adding, please wait'
  StartMacro = DoWatchAddProgress(key_combo='%{a}')
  
class WaitWhileAddingFolder(Task.RunWaitReport):
  Name = 'adding folder, please wait'
  StartMacro = DoWatchAddProgress(key_combo='%{w}')
    
class BrowseArchive(Task.FormFill):
  # browse through the list of archive items
  Name = 'browse archive'
  Permanence = Task.NO_COMPLETE
  CancelMacro = UIA.EndWindowByButton()
  contents_path = '/client[3]/window[4]/list[3]'
  extract_path = '/client[3]/window[1]/client[3]/window[0]/tool bar[3]/push button[4]'

  def OnInit(self):
    model = Adapters.ColumnList(self, self.contents_path, 'Filename', 
                                ('Filename', 'Type', 'Modified', 'Size', 'CRC'))
    self.AddField(FileView(self, model, 'contents', 'file'))
    
    # define a condition for extracting files
    def ExtractCondition():
      c = Interface.IContext(self).GetObjectAt(self.extract_path)
      try: return not c.IsNotReady()
      except: return False
    
    self.AddContextOption(AddFile, True)
    self.AddContextOption(AddFolder, True)    
    self.AddContextOption(ExtractFile, True, ExtractCondition)
    self.AddContextOption(ExtractAllFiles, True, ExtractCondition)
    
  def UpdateName(self):
    # pretty up the name of the browse task
    try:
      name = self.model.Name
      tmp, fn = name.split('-')
      self.Name = 'browse archive %s' % fn
    except:
      return
  
  def OnLoseFocus(self, message):
    # update the name of the task
    self.UpdateName()

  def OnGainFocus(self, message):
    # update the name of the task
    self.UpdateName()
    
class ChooseArchiveStep(Task.FileOpening):
  # let the user choose an archive to open
  StartMacro = UIA.StartWindowByKey(key_combo='^{o}', ClassName='#32770', 
                                    Name='Open Archive')
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  CancelMacro = UIA.EndWindowByButton()
  filename_path = Task.FileOpening.EXTENDED_FILENAME_PATH
                                    
  def OnInit(self):
    # set filename filters
    self.FilterByExtension('zip', 'tar', 'tgz')
    
class CreateArchiveStep(Task.FileSaving):
  # let the user choose the name for a new archive and location
  StartMacro = UIA.StartWindowByKey(key_combo='^{n}', ClassName='#32770', 
                                    Name='New Archive')
  CompleteMacro = DoEndCreateArchiveWithoutAdd()
  CancelMacro = UIA.EndWindowByButton()
  filename_path = Task.FileSaving.EXTENDED_FILENAME_PATH
  
  def OnInit(self):
    # set filename filters
    self.FilterByExtension('zip')

class ChooseAddFileStep(Task.FileOpening):
  # let the user add one file to the archive
  Name = 'choose a file'
  Modal = True
  filename_path = Task.FileOpening.EXTENDED_FILENAME_PATH
  
class SetAddFileOptionsStep(Task.FormFill):
  Name = 'set add file options'
  option_paths =['/dialog[3]/window[16]/property page[3]/window[19]/check box[3]', # full path info
                 '/dialog[3]/window[16]/property page[3]/window[15]/check box[3]'] # encrypt
                 
  def OnInit(self):
    # add all the options
    for p in self.option_paths:
      model = UIA.Adapters.CheckBox(self, p)
      self.AddField(Control.List(self, model))

class AddFile(Task.Wizard):
  Name = 'add a file'
  Successor = WaitWhileAdding
  StartMacro = UIA.StartWindowByKey(key_combo='+{a}', ClassName='#32770',
                                    Name='Add')
  #CompleteMacro = UIA.EndWindowByKey(key_combo='%(a)')
  CancelMacro = UIA.EndWindowByButton()
  Modal = True
  
  def OnInit(self):
    self.AddStep(ChooseAddFileStep)
    self.AddStep(SetAddFileOptionsStep)
   
class ChooseAddFolderStep(Task.FolderBrowsing):
  Name = 'choose a folder'
  Modal = True
  filename_path = Task.FolderBrowsing.EXTENDED_FILENAME_PATH
  
  def BuildPath(self, current):
    # append *.* onto the final pathname and put in quotes
    return '"%s\\*.*"' % current
    
class SetAddFolderOptionsStep(SetAddFileOptionsStep):
  # let the user choose options for adding
  Name = 'set add folder options'
  more_options = ['/dialog[3]/window[16]/property page[3]/window[20]/check box[3]', # subfolders
                  '/dialog[3]/window[16]/property page[3]/window[16]/check box[3]'] # hidden

  def OnInit(self):
    self.option_paths.extend(self.more_options)
    super(SetAddFolderOptionsStep, self).OnInit()
      
class AddFolder(Task.Wizard):
  # choose destination, set options
  Name = 'add a folder'
  Modal = True
  Successor = WaitWhileAddingFolder
  StartMacro = UIA.StartWindowByKey(key_combo='+{a}', ClassName='#32770',
                                    Name='Add')
  #CompleteMacro = DoAddWithWildcards()
  CancelMacro = UIA.EndWindowByButton()

  def OnInit(self):
    self.AddStep(ChooseAddFolderStep)
    self.AddStep(SetAddFolderOptionsStep)

class ChooseExtractFolderStep(Task.FolderBrowsing):
  # let the user choose the destination folder for extracted files
  Name = 'choose destination folder'
  Modal = True
  filename_path = '/dialog[3]/window[1]/combo box[3]/window[0]/editable text[3]'
    
class SetExtractOptionsStep(Task.FormFill):
  # let the user choose options for extraction
  Name = 'set extract options'
  option_paths = ['/dialog[3]/window[15]/check box[3]',
                  '/dialog[3]/window[16]/check box[3]',
                  '/dialog[3]/window[17]/check box[3]']
  
  def OnInit(self):
    # add all the options
    for p in self.option_paths:
      model = UIA.Adapters.CheckBox(self, p)
      self.AddField(Control.List(self, model))
    
class ExtractFile(Task.Wizard):
  # choose destination, set options
  Name = 'extract current file'
  Modal = True
  Successor = WaitWhileExtracting
  StartMacro = UIA.StartWindowByKey(key_combo='+{e}', ClassName='#32770',
                                    Name='Extract')
  CancelMacro = UIA.EndWindowByButton()
  #CompleteMacro = UIA.EndWindowByKey(key_combo='%{e}')
  Successor = WaitWhileExtracting
  
  def OnInit(self):
    self.AddStep(ChooseExtractFolderStep)
    self.AddStep(SetExtractOptionsStep)
    
class ExtractAllFiles(ExtractFile):
  # select all files, choose the destination, set options
  Name = 'extract all files'
  StartMacro = DoSelectAllThenExtract()
  
class NewArchive(Task.Wizard):
  # create a new archive, browse it
  Name = 'new archive'
  Successor = BrowseArchive
  count = 1
  StartMacro = DoStartNewWindow()
  CancelMacro = UIA.EndWindowByButton()
    
  def OnInit(self):
    # add the steps: create archive
    self.AddStep(CreateArchiveStep)
  
  def OnLoseFocus(self, message):
    self.UpdateName()
    
  def UpdateName(self):
    # pretty up the name of untitled archives
    try:
      name = self.model.Name
    except:
      return
    tname = self.__class__.Name
    unnamed = True
    try:
      tmp, fn = name.split(' - ')
      unnamed = (name in ('WinZip', 'Winzip (Evaluation Version)'))
    except ValueError:
      pass
    if unnamed and not self.Name.startswith('continue %s ' % tname):
      self.Name = 'continue %s %d' % (tname, self.__class__.count)
      self.__class__.count += 1
    elif not unnamed:
      self.Name = 'continue %s %s' % (tname, fn)
    
class OpenArchive(NewArchive):
  # open an existing archive, browse it
  Name = 'open archive'
  
  def OnInit(self):
    # add the steps: choose archive file
    self.AddStep(ChooseArchiveStep)
    
class AutoOpenDialog(Task.RunWaitReport):
  Modal = True
  Name = 'archive exists, opening'
  Permanence = Task.NO_CANCEL
  yes_path = '/dialog[3]/window[0]/push button[3]'
  CompleteMacro = UIA.WaitEndWindowByButton(button_path=yes_path)
  
  def OutWaiting(self, message, auto_focus):
    p1, p2 = super(AutoOpenDialog, self).OutWaiting(message, auto_focus)
    p2.UpdateMessage(Output.SUMMARY, listen=True)
    return (p1, p2)
  
  def OnSayDone(self, message):
    self.CompleteMacro.Continue()
   
  def Trigger(cls, event, model, container):
    return not (model.State & UIA.Constants.STATE_SYSTEM_SIZEABLE) and \
           model.Name == 'WinZip' and model.ClassName == '#32770'
  Trigger = classmethod(Trigger)

Tasks = [NewArchive, OpenArchive]
AutoTasks = [AutoOpenDialog]
