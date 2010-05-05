'''
Perceived Usefulness and Ease of Use questionnaire

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

SURVEY_PATH = '../studies/survey.py'

# grouping /client[3]/window[0]/client[3]/window[2]/grouping[3]
# label /client[3]/window[0]/client[3]/window[3]/text[3]
# unlikely /client[3]/window[0]/client[3]/window[4]/text[3]
# 1 /client[3]/window[0]/client[3]/window[5]/radio button[3]
# 2 /client[3]/window[0]/client[3]/window[6]/radio button[3]
# 3 /client[3]/window[0]/client[3]/window[7]/radio button[3]
# 4 /client[3]/window[0]/client[3]/window[8]/radio button[3]
# 5 /client[3]/window[0]/client[3]/window[9]/radio button[3]
# 6 /client[3]/window[0]/client[3]/window[10]/radio button[3]
# 7 /client[3]/window[0]/client[3]/window[11]/radio button[3]
# likely /client[3]/window[0]/client[3]/window[12]/text[3]
# ...
# OK button /client[3]/window[0]/client[3]/window[135]/push button[3]
# goes left to right, not top down

class Main(UIA.Macro):
  def Sequence(self):
    # do nothing when program starts, let tasks decide what to do
    yield True

class DoStartSurvey(UIA.Macro):
  def Sequence(self):
    self.WatchForNewWindow(Name='Usefulness and Ease of Use',
                           ClassName='wxWindowClassNR')
    self.RunFile('python %s p %s' % (SURVEY_PATH,
                                     self.survey_name))
    yield False
    yield True

class Questionnaire(Task.FormFill):
  #Permanence = Task.NO_CANCEL
  help_path = '/client[3]/window[0]/client[3]/window[1]/editable text[3]'
  ok_path = '/client[3]/window[0]/client[3]/window[135]/push button[3]'
  label_path = '/client[3]/window[0]/client[3]/window[%d]/text[3]'
  button_path = '/client[3]/window[0]/client[3]/window[%d]/radio button[3]'

  CompleteMacro = UIA.EndWindowByButton(button_path=ok_path)
  CancelMacro = UIA.EndWindowByButton()

  def OnInit(self):
    help = Adapters.TextBox(self, self.help_path)
    self.AddField(Control.TextReading(self, help, spell=False))
    # extra labels for likely and unlikely
    labels = {0 : '1, unlikely', 6 : '7, likely'}
    # 6 usefulness questions
    for i in xrange(6):
      label, buttons = self.getUsefulnessPath(i)
      bl = Adapters.ButtonList(self, buttons, labels=labels, curr=3)
      lb = Adapters.TextLabel(self, label)
      self.AddField(Control.List(self, bl, lb))
    # 6 ease of use questions
    for i in xrange(6):
      label, buttons = self.getEaseOfUsePath(i)
      bl = Adapters.ButtonList(self, buttons, labels=labels, curr=3)
      lb = Adapters.TextLabel(self, label)
      self.AddField(Control.List(self, bl, lb))

  def getEaseOfUsePath(self, n):
    # 1, 3, 5, 7, 9, 11
    buttons = []
    start = 11*(n*2)+16
    end = start + 7
    for i in range(start, end):
      buttons.append(self.button_path % i)
    return (self.label_path % (start-2)), buttons

  def getUsefulnessPath(self, n):
    # 0, 2, 4, 6, 8, 10
    buttons = []
    start = 11*(n*2)+5
    end = start + 7
    for i in range(start, end):
      buttons.append(self.button_path % i)
    return (self.label_path % (start-2)), buttons

class Speech(Questionnaire):
  Name = 'concurrent speech questionnaire'
  StartMacro = DoStartSurvey(survey_name = 'speech')

class Search(Questionnaire):
  Name = 'search questionnaire'
  StartMacro = DoStartSurvey(survey_name = 'search')

class Memory(Questionnaire):
  Name = 'memory questionnaire'
  StartMacro = DoStartSurvey(survey_name = 'memory')  
  
class Learning(Questionnaire):
  Name = 'learning questionnaire'
  StartMacro = DoStartSurvey(survey_name = 'learning')

class Workflow(Questionnaire):
  Name = 'workflow questionnaire'
  StartMacro = DoStartSurvey(survey_name = 'workflow')

Tasks = [Speech, Search, Memory, Learning, Workflow]
AutoTasks = []
