'''
Microsoft Notepad (XP)

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import UIA
from UIA import Adapters
from View import Task, Control

class Main(UIA.Macro):
  def Sequence(self):
    # do nothing on start
    yield True

class DoStartDocumentWindow(UIA.Macro):
  def Sequence(self):
    # watch for notepad window
    self.WatchForNewWindow(Name='Untitled - Notepad', ClassName='Notepad')
    # run the notepad application
    self.RunFile('notepad.exe')
    yield False
    yield True

class DoCloseDocumentWindow(UIA.Macro):
  def Sequence(self):
    # watch for the are you sure dialog
    self.WatchForNewWindow(Name='Notepad', ClassName='#32770', name='confirm')
    # watch for the window closing
    self.WatchForWindowClose(self.model.Window, 'done')
    # close the window
    self.CloseWindow()
    yield False
    print '********* continuing:', self.name
    # close the confirmation dialog if it appears
    if self.name == 'confirm':
      self.SendKeys('N')
    yield True

class DoSaveFile(UIA.Macro):
  def Sequence(self):
    # press the save hotkey
    self.SendKeys('^{s}')
    yield True

class SaveFile(Task.RunAndReport):
  Name = 'save file'
  StartMacro = DoSaveFile()

class SaveFileAs(Task.FileSaving):
  # let the user choose a filename and location to save
  Name = 'save file as'
  Modal = True
  StartMacro = UIA.StartWindowByKey(key_combo='%{f}a',
                                    Name='Save as',
                                    ClassName='#32770')
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  CancelMacro = UIA.EndWindowByButton()
  filename_path = Task.FileSaving.EXTENDED_FILENAME_PATH

  def OnInit(self):
    self.FilterByExtension('txt')

class OpenFileStep(Task.FileOpening):
  # let the user choose a file to open
  StartMacro = UIA.StartWindowByKey(key_combo='^{o}', ClassName='#32770',
                                    Name='Open')
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  CancelMacro = UIA.EndWindowByButton()
  filename_path = Task.FileOpening.EXTENDED_FILENAME_PATH

class EditDocument(Task.FormFill):
  # allow the user to edit the document
  Name = 'new document'
  Permanence = Task.NO_COMPLETE
  body_path = '/client[3]/window[0]/editable text[3]'
  count = 1
  CancelMacro = DoCloseDocumentWindow()

  def OnInit(self):
    doc = Adapters.EditableTextBox(self, self.body_path)
    self.AddField(Control.TextEntry(self, doc, 'document'))

    # condition for save without save dialog
    def SaveCond():
      self.UpdateName()
      return not self.Name.startswith('edit untitled ')

    # always offer save as, but only offer save if file already has a name
    self.AddContextOption(SaveFileAs, True)
    self.AddContextOption(SaveFile, True, SaveCond)

  def OnGainFocus(self, message):
    self.UpdateName()

  def OnLoseFocus(self, message):
    self.UpdateName()

  def UpdateName(self):
    # pretty up the name of untitled documents
    try:
      name = self.model.Name
    except:
      return
    fn, tmp = name.split(' - ')
    unnamed = (name == 'Untitled - Notepad')
    if unnamed and not self.Name.startswith('edit untitled '):
      self.Name = 'edit untitled %d' % EditDocument.count
      EditDocument.count += 1
    elif not unnamed:
      self.Name = 'edit %s' % fn

class NewDocument(EditDocument):
  # start a new document and then let the user edit it
  StartMacro = DoStartDocumentWindow()

class OpenDocument(Task.Wizard):
  # open an existing document and then let the user edit it
  Name = 'open document'
  Successor = EditDocument
  count = 1
  StartMacro = DoStartDocumentWindow()
  CancelMacro = UIA.EndWindowByButton()

  def OnInit(self):
    self.AddStep(OpenFileStep)

  def OnLoseFocus(self, message):
    # give the open task a meaningful name
    unnamed = (self.Name == OpenDocument.Name)
    if unnamed:
      self.Name = 'continue opening file %d' % OpenDocument.count
      OpenDocument.count += 1
    else:
      pass

class AutoConfirmDialog(Task.FormFill):
  Modal = True
  Name = 'confirm overwrite'
  Permanence = Task.NO_CANCEL
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  yes_path = '/dialog[3]/window[0]/push button[3]'
  no_path = '/dialog[3]/window[1]/push button[3]'
  text_path = '/dialog[3]/window[3]/text[3]'

  def OnInit(self):
    bl = Adapters.ButtonList(self, [self.no_path, self.yes_path])
    label = Adapters.TextLabel(self, self.text_path)
    self.AddField(Control.List(self, bl, label))
    
  def Trigger(cls, event, model, container):
    return not (model.State & UIA.Constants.STATE_SYSTEM_SIZEABLE) and \
           model.Name.startswith('Save') and model.ClassName == '#32770'
  Trigger = classmethod(Trigger)

Tasks = [NewDocument, OpenDocument]
AutoTasks = [AutoConfirmDialog]
