'''
Microsoft Outlook Express (XP)

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
from UIA import Adapters
from View import Task, Control

# path reused through the script
save_attach_path = '/client[3]/window[5]/client[3]/window[1]/client[3]/window[0]/client[3]/window[1]/tool bar[3]/push button[5]'

class Main(UIA.Macro):
  # the macro that's run at the very start of the program
  def Sequence(self):
    # watch for outlook
    self.WatchForNewWindow(Name='Outlook Express',
                           ClassName='Outlook Express Browser Class')
    # run outlook
    self.RunFile('msimn.exe')
    yield False
    yield True

class DoResendMessage(UIA.Macro):
  def Sequence(self):
    # watch for message window
    self.WatchForNewWindow(ClassName='ATH_Note')
    # open waiting message
    self.SendKeys('^{o}')
    yield False
    # watch for window close
    self.WatchForWindowClose(self.result.Window)
    # send message
    self.SendKeys('%{s}')
    yield False
    yield True

class DoCancelMessageNoConfirm(UIA.Macro):
  def Sequence(self):
    # watch for the are you sure dialog
    self.WatchForNewWindow(Name='Outlook Express', ClassName='#32770',
                           name='confirm')
    # watch for the window closing
    self.WatchForWindowClose(self.model.Window, 'done')
    # close the window
    self.CloseWindow()
    yield False
    # close the confirmation dialog if it appears
    if self.name == 'confirm':
      self.SendKeys('N')
    yield True

class DoSelectSaveAttachments(UIA.Macro):
  def Sequence(self):
    # watch for the attachments dialog
    self.WatchForNewWindow(ClassName='#32770', Name='Save Attachments')
    # give the button the focus
    c = self.model.ChildFromPath(save_attach_path)
    c.SetFocus()
    c.SendKeys('{ENTER}{UP}{ENTER}')
    yield False
    yield True

class DoSelectTaskTab(UIA.Macro):
  tab_list_path = '/dialog[3]/window[14]/page tab list[3]'
  tab_path = '/dialog[3]/window[14]/page tab list[3]/page tab[0]'
  def Sequence(self):
    tab_list = self.model.ChildFromPath(self.tab_list_path)
    tab = self.model.ChildFromPath(self.tab_path)
    tab_list.Select(UIA.Constants.SELFLAG_TAKEFOCUS)
    tab.Select(UIA.Constants.SELFLAG_TAKEFOCUS)
    yield True

class ResendMessage(Task.RunAndReport):
  Name = 'resend message'
  StartMacro = DoResendMessage()

class AttachFiles(Task.FileOpening):
  Name = 'attach files'
  Modal = True
  StartMacro = UIA.StartWindowByKey(key_combo='%{i}a', ClassName='#32770',
                                    Name='Insert Attachment')
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  CancelMacro = UIA.EndWindowByButton()
  filename_path = '/dialog[3]/window[7]/editable text[3]'

class ChooseFolderStep(Task.FolderBrowsing):
  Name = 'choose destination folder'
  Modal = True
  filename_path = '/dialog[3]/window[6]/editable text[3]'

class ChooseAttachmentStep(Task.FormFill):
  Name = 'choose one attachment to save'
  Modal = True
  attachments_path = '/dialog[3]/window[4]/list[3]'

  def OnInit(self):
    l = Adapters.List(self, self.attachments_path)
    self.AddField(Control.List(self, l, name='', label='file'))

class SaveOneAttachment(Task.Wizard):
  Name = 'save one attachment'
  Modal = True
  StartMacro = DoSelectSaveAttachments()
  CancelMacro = UIA.EndWindowByButton()
  CompleteMacro = UIA.EndWindowByKey(key_combo='%{s}')

  def OnInit(self):
    self.AddStep(ChooseAttachmentStep)
    self.AddStep(ChooseFolderStep)

class SaveAllAttachments(SaveOneAttachment):
  Name = 'save all attachments'

  def OnInit(self):
    self.AddStep(ChooseFolderStep)

class MoveMail(Task.FormFill):
  Name = 'move message to mailbox'
  Modal = True
  folders_path = '/dialog[3]/window[1]/client[3]/window[0]/outline[3]'
  ok_path = '/dialog[3]/window[2]/push button[3]'
  StartMacro = UIA.StartWindowByKey(key_combo='^(+(v))', ClassName='#32770',
                                    Name='move')
  CancelMacro = UIA.EndWindowByButton()
  CompleteMacro = UIA.EndWindowByButton(button_path=ok_path)

  def OnInit(self):
    t = Adapters.Tree(self, self.folders_path)
    self.AddField(Control.Tree(self, t, 'mailboxes', 'mailbox'))

  def IsValid(self):
    ok = Interface.IContext(self).GetObjectAt(self.ok_path)
    if not (ok.State & UIA.Constants.STATE_SYSTEM_UNAVAILABLE):
      return None
    else:
      return 'The message cannot be moved to the selected folder.'

class WriteMail(Task.FormFill):
  Name = 'write mail'
  StartMacro = UIA.StartWindowByKey(ClassName='ATH_Note', key_combo='%f{ENTER 2}')
  CompleteMacro = UIA.EndWindowByKey(key_combo='%{s}')
  CancelMacro = DoCancelMessageNoConfirm()
  to_path = '/client[3]/window[2]/client[3]/window[3]/editable text[3]'
  cc_path = '/client[3]/window[2]/client[3]/window[4]/editable text[3]'
  subject_path = '/client[3]/window[2]/client[3]/window[5]/editable text[3]'
  attachments_path = '/client[3]/window[2]/client[3]/window[2]/list[3]'
  body_path = '/client[3]/window[3]/client[3]/window[0]/client[3]/client[0]'

  def OnInit(self):
    # recepient line
    t = Adapters.EditableTextBox(self, self.to_path, multiline=False)
    self.AddField(Control.TextEntry(self, t, 'recipient', spell=False))
    # carbon copies line
    t = Adapters.EditableTextBox(self, self.cc_path, multiline=False)
    self.AddField(Control.TextEntry(self, t, 'carbon copies',spell=False))
    # subject line
    t = Adapters.EditableTextBox(self, self.subject_path, multiline=False)
    self.AddField(Control.TextEntry(self, t, 'subject'))
    # attachments list
    l = Adapters.EditableList(self, self.attachments_path)
    self.AddField(Control.List(self, l, 'attachments'))
    # body field
    doc = Adapters.EditableDocument(self, self.body_path)
    self.AddField(Control.TextEntry(self, doc, 'message body'))

    # add all secondary task options
    self.AddContextOption(AttachFiles, True)

  def OnLoseFocus(self, message):
    text = self.fields[2].Model.GetAllText()
    if text:
      self.Name = 'continue new message with subject, %s' % text
    else:
      self.Name = 'continue new message'

  def IsValid(self):
    #@todo: not checking email validity
    return None
    regex = '^([^@;,]+@[^@;, ]+(;|,)?\W*)+$'
    # make sure there's at least one valid email address in the to field
    to = self.fields[0].Model.GetAllText()
    if re.match(regex, to) is None:
      return 'Invalid email address as recipient.'
    # make sure all email addresses in the cc field are valid
    cc = self.fields[1].Model.GetAllText()
    if cc != '' and re.match(regex, cc) is None:
      return 'Invalid email address in carbon copies.'
    return None

class ReplyMail(WriteMail):
  Name = 'reply to sender'
  StartMacro = UIA.StartWindowByKey(key_combo='^{r}', ClassName='ATH_Note')

  def OnInit(self):
    # replies have no access to the to field, and start in the message body
    t = Adapters.EditableTextBox(self, self.cc_path, multiline=False)
    self.AddField(Control.TextEntry(self, t, 'carbon copies',spell=False))
    t = Adapters.EditableTextBox(self, self.subject_path, multiline=False)
    self.AddField(Control.TextEntry(self, t, 'subject'))
    l = Adapters.EditableList(self, self.attachments_path)
    self.AddField(Control.List(self, l, 'attachments'))
    doc = Adapters.EditableDocument(self, self.body_path)
    self.AddField(Control.TextEntry(self, doc, 'message body'))
    self.curr = 3
    # add all secondary task options
    self.AddContextOption(AttachFiles, True)

  def IsValid(self):
    # replies are always valid
    return None

  def OnLoseFocus(self, message):
    text = self.fields[1].Model.GetAllText()
    if text:
      self.Name = 'continue reply with subject, %s' % text
    else:
      self.Name = 'continue reply'

class ForwardMail(WriteMail):
  Name = 'forward message'
  StartMacro=UIA.StartWindowByKey(key_combo='^{f}', ClassName='ATH_Note')

  def OnLoseFocus(self, message):
    text = self.fields[2].Model.GetAllText()
    if text:
      self.Name = 'continue forward with subject, %s' % text
    else:
      self.Name = 'continue forward'
      
class HighlightReading(Control.TextReading):
  start = 0
  def OnRemember(self, message):
    mailbox = self.parent.views[1].Model
    if message.Press:
      Config.log(mailbox.GetSelectedName())
      self.start = self.Model.Chunk.GetCurrentWordBounds()[0]
      if self.start < 0:
        self.start = 0
    else:
      end = self.Model.Chunk.GetCurrentWordBounds()[1]
      Config.log('%d %d' % (self.start, end))
    message.Stop = False

class BrowseMail(Task.LinkedBrowsing):
  Name = 'browse mail'
  Permanence = Task.NO_START|Task.NO_END
  reply_path = '/client[3]/window[1]/client[3]/window[0]/client[3]/window[0]/tool bar[3]/push button[1]'
  forward_path = '/client[3]/window[1]/client[3]/window[0]/client[3]/window[0]/tool bar[3]/push button[2]'
  mailboxes_path = '/client[3]/window[4]/client[3]/window[0]/client[3]/window[1]/client[3]/window[0]/outline[3]'
  messages_path = '/client[3]/window[5]/client[3]/window[0]/client[3]/window[0]/list[3]'
  preview_path = '/client[3]/window[5]/client[3]/window[1]/client[3]/window[0]/client[3]/client[0]/pane[0]'

  def OnInit(self):
    # create models
    cl = Adapters.EditableColumnList(self, self.messages_path, 'Person',
                                     ('Person', 'Subject', 'Received'))
    tr = Adapters.Tree(self, self.mailboxes_path)
    ht = Adapters.SimpleDocument(self, self.preview_path)

    # create and add views in order of influence
    folders = Control.Tree(self, tr, 'mailboxes', label='sibling mailbox')
    messages = Control.List(self, cl, 'messages', label='message',
                            order=['Received', 'Sent'])
    body = HighlightReading(self, ht, 'email body', spell=False)
    self.AddView(folders)
    self.AddView(messages)
    self.AddView(body)

    # define a condition for reply and forward tasks
    def ReplyAndForwardCondition():
      c = Interface.IContext(self).GetObjectAt(self.reply_path)
      try: return not c.IsNotReady()
      except: return False

    # a condition for saving attachments
    def SaveAttachmentsCondition():
      c = Interface.IContext(self).GetObjectAt(save_attach_path)
      try: return not c.IsNotReady()
      except: return False

    # and a condition for resending failed messages
    def ResendMessageCondition():
      name = Interface.IFiniteCollection(self.views[0].Model).GetSelectedName()
      return name == 'Outbox'

    # add secondary tasks to the appropriate controls
    messages.AddContextOption(ReplyMail, True, ReplyAndForwardCondition)
    messages.AddContextOption(ForwardMail, True, ReplyAndForwardCondition)
    messages.AddContextOption(SaveAllAttachments, True, SaveAttachmentsCondition)
    messages.AddContextOption(SaveOneAttachment, True, SaveAttachmentsCondition)
    messages.AddContextOption(ResendMessage, True, ResendMessageCondition)
    messages.AddContextOption(MoveMail, True)
    body.AddContextOption(ReplyMail, True, ReplyAndForwardCondition)
    body.AddContextOption(ForwardMail, True, ReplyAndForwardCondition)
    body.AddContextOption(SaveAllAttachments, True, SaveAttachmentsCondition)
    body.AddContextOption(SaveOneAttachment, True, SaveAttachmentsCondition)
    body.AddContextOption(ResendMessage, True, ResendMessageCondition)
    body.AddContextOption(MoveMail, True)

class AutoConfirmNoSubject(Task.FormFill):
  Modal = True
  Name = 'confirm no subject'
  Permanence = Task.NO_CANCEL
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  ok_path = '/dialog[3]/window[0]/push button[3]'
  cancel_path = '/dialog[3]/window[1]/push button[3]'
  text_path = '/dialog[3]/window[5]/text[3]'
  check_path = '/dialog[3]/window[3]/check box[3]'

  def OnInit(self):
    bl = Adapters.ButtonList(self, [self.ok_path, self.cancel_path])
    label = Adapters.TextLabel(self, self.text_path)
    self.AddField(Control.List(self, bl, label))
    cb = Adapters.CheckBox(self, self.check_path)
    self.AddField(Control.List(self, cb))

  def Trigger(cls, event, model, container):
    return not (model.State & UIA.Constants.STATE_SYSTEM_SIZEABLE) and \
           model.Name == 'Outlook Express' and model.ClassName == '#32770' and \
           isinstance(container.GetTask(-1), WriteMail)
  Trigger = classmethod(Trigger)

class AutoConfirmDeleteFromTrash(Task.FormFill):
  Modal = True
  Name = 'confirm deletion'
  Permanence = Task.NO_CANCEL
  CompleteMacro = UIA.EndWindowByKey(key_combo='{ENTER}')
  ok_path = '/dialog[3]/window[0]/push button[3]'
  cancel_path = '/dialog[3]/window[1]/push button[3]'
  delete_msg = 'Are you sure you want to permanently delete this message?'

  def OnInit(self):
    bl = Adapters.ButtonList(self, [self.cancel_path, self.ok_path])
    self.AddField(Control.List(self, bl, self.delete_msg))

  def Trigger(cls, event, model, container):
    return not (model.State & UIA.Constants.STATE_SYSTEM_SIZEABLE) and \
           model.Name == 'Outlook Express' and model.ClassName == '#32770' and \
           model.GetChild(3).ChildCount == 4
  Trigger = classmethod(Trigger)

class AutoSendError(Task.FormFill):
  Modal = True
  Name = 'send error'
  Permanence = Task.NO_CANCEL
  CompleteMacro = UIA.HideWindowByKey(key_combo='%h')
  StartMacro = DoSelectTaskTab
  list_path = '/dialog[3]/window[12]/list[3]'

  def OnInit(self):
    cl = Adapters.ColumnList(self, self.list_path, name_key='Action',
                             primary_keys=['Action', 'Status'])
    self.AddField(Control.List(self, cl, 'error list'))

  def Trigger(cls, event, model, container):
    return not (model.State & UIA.Constants.STATE_SYSTEM_SIZEABLE) and \
           model.Name == 'Outlook Express' and model.ClassName == '#32770' and \
           model.GetChild(3).ChildCount == 17
  Trigger = classmethod(Trigger)

Tasks = [BrowseMail, WriteMail]
AutoTasks = [AutoConfirmNoSubject, AutoConfirmDeleteFromTrash, AutoSendError]
