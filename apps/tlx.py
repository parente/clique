'''
NASA Task Load Index

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

class Main(UIA.Macro):
  def Sequence(self):
    # do nothing when program starts, let tasks decide what to do
    yield True

class DoStartRatings(UIA.Macro):
  def Sequence(self):
    self.WatchForNewWindow(Name='Workload Ratings',
                           ClassName='wxWindowClassNR')
    self.RunFile('python %s r %s' % (SURVEY_PATH,
                                     self.survey_name))
    yield False
    yield True

class DoStartSources(UIA.Macro):
  def Sequence(self):
    self.WatchForNewWindow(Name='Workload Sources',
                           ClassName='wxWindowClassNR')
    self.RunFile('python %s s %s' % (SURVEY_PATH,
                                     self.survey_name))
    yield False
    yield True

class Ratings(Task.FormFill):
  help_path = '/client[3]/window[0]/client[3]/window[1]/editable text[3]'
  ok_path = '/client[3]/window[0]/client[3]/window[147]/push button[3]'
  grouping_path = '/client[3]/window[0]/client[3]/window[%d]/grouping[3]'
  question_path = '/client[3]/window[0]/client[3]/window[%d]/text[3]'
  button_path = '/client[3]/window[0]/client[3]/window[%d]/radio button[3]'

  # instructions label /client[3]/window[0]/client[3]/window[0]/text[3]
  # help /client[3]/window[0]/client[3]/window[1]/editable text[3]
  # grouping /client[3]/window[0]/client[3]/window[2]/grouping[3]
  # low /client[3]/window[0]/client[3]/window[3]/text[3]
  # radio /client[3]/window[0]/client[3]/window[4]/radio button[3]
  # ...
  # radio /client[3]/window[0]/client[3]/window[23]/radio button[3]
  # high /client[3]/window[0]/client[3]/window[24]/text[3]
  # help /client[3]/window[0]/client[3]/window[25]/text[3]
  # grouping ...
  # help /client[3]/window[0]/client[3]/window[145]/text[3]
  # OK /client[3]/window[0]/client[3]/window[147]/push button[3]

  CompleteMacro = UIA.EndWindowByButton(button_path=ok_path)
  CancelMacro = UIA.EndWindowByButton()

  def OnInit(self):
    help = Adapters.TextBox(self, self.help_path)
    self.AddField(Control.TextReading(self, help, spell=False))
    gen = dict(((x, str(x+1)) for x in xrange(1, 19)))
    # extra labels for low to high
    labels = {0 : '1, low', 19 : '20, high'}
    labels.update(gen)
    # labels from good to poor
    perf = {0 : '1, good', 19 : '20, poor'}
    perf.update(gen)
    for i in range(6):
      g, q, b = self.getPaths(i)
      # grouping label for instructions
      gl = Adapters.TextLabel(self, g, template='%s instructions')
      # question with group label
      x = Adapters.TextBox(self, q)
      self.AddField(Control.TextReading(self, x, spell=False, name=gl))
      # radio buttons with numeric labels and group label
      if i == 4:
        # second to last has good to poor instead of low to high
        x = Adapters.ButtonList(self, b, labels=perf)
      else:
        x = Adapters.ButtonList(self, b, labels=labels)
      # grouping label for ratings
      gl = Adapters.TextLabel(self, g, template='%s ratings')
      self.AddField(Control.List(self, x, name=gl))

  def getPaths(self, n):
    button_paths = []
    start = (24*n)+4
    end = start + 20
    grouping_path = self.grouping_path % (start-2)
    question_path = self.question_path % (end+1)
    for i in range(start, end):
      button_paths.append(self.button_path % i)
    return grouping_path, question_path, button_paths

class Sources(Task.FormFill):
  help_path = '/client[3]/window[0]/client[3]/window[1]/editable text[3]'
  ok_path = '/client[3]/window[0]/client[3]/window[48]/push button[3]'
  button_path = '/client[3]/window[0]/client[3]/window[%d]/radio button[3]'

  # instructions /client[3]/window[0]/client[3]/window[0]/text[3]
  # help /client[3]/window[0]/client[3]/window[1]/editable text[3
  # grouping /client[3]/window[0]/client[3]/window[2]/grouping[3]
  # radio1 /client[3]/window[0]/client[3]/window[3]/radio button[3]
  # radio2 /client[3]/window[0]/client[3]/window[4]/radio button[3]
  # grouping ...
  # radio2 /client[3]/window[0]/client[3]/window[46]/radio button[3]
  # OK /client[3]/window[0]/client[3]/window[48]/push button[3]

  CompleteMacro = UIA.EndWindowByButton(button_path=ok_path)
  CancelMacro = UIA.EndWindowByButton()

  def OnInit(self):
    help = Adapters.TextBox(self, self.help_path)
    self.AddField(Control.TextReading(self, help, spell=False))
    # generate pair names
    labels = []
    for i in range(1, 16):
      labels.append('pair %d' % i)
    # all button list pairs
    for i in range(0, 15):
      start = (i*3) + 3
      paths = [self.button_path % start,
               self.button_path % (start+1)]
      bl = Adapters.ButtonList(self, paths)
      self.AddField(Control.List(self, bl, name=labels[i]))

class JAWSSources(Sources):
  Name = 'jaws sources'
  StartMacro = DoStartSources(survey_name = 'jaws_sources')

class CliqueSources(Sources):
  Name = 'clique sources'
  StartMacro = DoStartSources(survey_name = 'clique_sources')

class JAWSRatings(Ratings):
  Name = 'jaws ratings'
  StartMacro = DoStartRatings(survey_name = 'jaws_ratings')

class CliqueRatings(Ratings):
  Name = 'clique ratings'
  StartMacro = DoStartRatings(survey_name = 'clique_ratings')

Tasks = [JAWSSources, CliqueSources, JAWSRatings, CliqueRatings]
AutoTasks = []
