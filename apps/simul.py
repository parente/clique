'''
Simultaneous speech trial

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import random, time
import UIA, Output, View
from View import Task

DELAY = 2
SOUND = 'simul/%s.wav'

names = [
         'William Smith',
         'Jacob Paxton',
         'Marla Andrews',
         'John Finch',
         'Jessie Marsh',
         'Jodie Wendell',
         'Wilbur Fox',
         'Nathan Ashley',
         'Jonathan Brody',
         'Paul Strong',
         'Myra Irington',
         'Mark Applewood',
         'Austin Howards',
         'Gwen Poultin',
         'Agnes Jerrald',
         'Chris Wisen',
         'Cathy Gates',
         'Phillip Ocean',
         'Thomas Monsdale',
         'Diane Nelson',
         'Nelson Bates',
         'Jerrald Howard',
         'Howard Buxton',
         'Larry White',
         'Bart Englewood',
         'Edward Simpson',
         'Walter Paradise',
         'Amy Hunter',
         'Jill Tayler',
         'Liz Horton',
         'Naomi Torrent',
         'Frank Ratcher',
         'Ken Longton',
         'Henry Watts',
         'Irene Pen',
         'Peter Glenn',
         'Gordon Xavier',
         'Ronald Miller',
         'Tyreek Ogdon',
         'Katy Orson',
         'Melissa Korn',
         'Jackie Sassen',
         'Valerie Forrest',
         'Tommy Danson',
         'Edwin Flock',
         'Kenneth Lars',
         'Finn Cheston',
         'Charles Baker',
         'Kerry Freeman',
         'Zeke Matthews',
         'Brice Davis',
         'Laura Reynolds',
         'Jessica Hamlin',
         'Jennifer Peterson',
         'Tara Perkins',
         'Sabrina Roberts',
         'Ben Gifford',
         'Adam Morgans',
         'Alice Goode',
         'Dom Passig',
         'Hank Trumbel',
         'Randy Malcolm',
         'Tyrone Flemming',
         'Janet Jameson',
         'Joyce Winters',
         'Shawn Testa',
         'Samuel Penta',
         'Norma Grady',
         'Lonnie Hawkins',
         'Belinda Smarts',
         'Sadie Green',
         'Zora Niles',
         'Grace Owin',
         'Andy Ebert',
         'Donny Jenkins',
         'Candice Felipe',
         'Wendy Young',
         'Jenna Moon',
         'Charlie Bond',
         'Sherry Ogden',
         'Vincent Manor',
         'Liz Martin',
         'George Minor',
         'Marty Stevens'
         ]

subjects = [
            'Please send now',
            'Please forward message',
            'Please resend email',
            'Please copy email',
            'Please delete email',
            'Please delete message',
            'Please send message',
            'Please email team',
            'Please email boss',
            'Forward email now',
            'Forward message soon',
            'Forward new email',
            'Forward attached file',
            'Forward old files',
            'Forward to team',
            'Forward to boss',
            'Reply and attach',
            'Reply to message',
            'Reply today please',
            'Reply to boss',
            'Reply with results',
            'Reply to team',
            'Reply with files',
            'Reply with news',
            'Save attachments first',
            'Save new emails',
            'Save old emails',
            'Save all messages',
            'Save my messages',
            'Save for team',
            'Save for boss',
            'Remember to reply',
            'Remember to forward',
            'Remember to save',
            'Remember to delete',
            'Remember to attach',
            'Remember to send',
            'Send email now',
            'Send email soon',
            'Send email quickly',
            'Send email today',
            'Send messages soon',
            'Send messages quickly',
            'Send response today',
            'Send team email',
            'Send private email',
            'Send email address',
            'Send all emails',
            'Send all files',
            'Send first files',
            'Send my files',
            'Send your files',
            'Respond with files',
            'Respond with news',
            'Respond with address',
            'Respond to emails',
            'Respond to messages',
            'Respond to team',
            'Respond to boss',
            'Delete last message',
            'Delete next message',
            'Delete all messages',
            'Delete team email',
            'File this message',
            'File this reply',
            'File new forwards',
            'File new emails',
            'File this email',
            'File old emails',
            'File last email',
            'File all messages',
            'Missing new emails',
            'Missing old messages',
            'Missing all mail',
            'Missing last email',
            'Missing last file',
            'Missing mail today',
            'Post new message',
            'Post new files',
            'Post old mail',
            'Post new addresses',
            'Post all addresses',
            'Post to boss',
            'Post to list'
            ]

combos = [('sender',   (1,2)),
          ('subject',  (1,2)),
          ('index',    (1,2)),
          ('total',    (1,2)),
          ('sender',   (1,3)),
          ('subject',  (1,3)),
          ('search',   (1,3)),
          ('sender',   (1,4)),
          ('subject',  (1,4)),
          ('length',   (1,4)),
          ('index',    (2,3)),
          ('total',    (2,3)),
          ('search',   (2,3)),
          ('index',    (2,4)),
          ('total',    (2,4)),
          ('length',   (2,4)),
          ('search',   (3,4)),
          ('length',   (3,4)),
          ('sender',   (1,2,3)),
          ('subject',  (1,2,3)),
          ('index',    (1,2,3)),
          ('total',    (1,2,3)),
          ('search',   (1,2,3)),
          ('sender',   (1,2,4)),
          ('subject',  (1,2,4)),
          ('index',    (1,2,4)),
          ('total',    (1,2,4)),
          ('length',   (1,2,4)),
          ('sender',   (1,3,4)),
          ('subject',  (1,3,4)),
          ('search',   (1,3,4)),
          ('length',   (1,3,4)),
          ('index',    (2,3,4)),
          ('total',    (2,3,4)),
          ('search',   (2,3,4)),
          ('length',   (2,3,4)),
          ('sender',   (1,2,3,4)),
          ('subject',  (1,2,3,4)),
          ('index',    (1,2,3,4)),
          ('total',    (1,2,3,4)),
          ('search',   (1,2,3,4)),
          ('length',   (1,2,3,4))
          ]

# randomize order of everything
random.shuffle(combos)
random.shuffle(names)
random.shuffle(subjects)
n = len(combos)
p = len(combos)/2

# pick practice materials
practice_msgs = zip(names[:p], subjects[:p], combos)
random.shuffle(combos)
trial_msgs = zip(names[p:p+n], subjects[p:p+n], combos)

class Main(UIA.Macro):
  def Sequence(self):
    yield True

class Trial(View.Base):
  def init(self, sender, subject, combo):
    self.target = combo[0]
    self.combo = combo[1]
    self.sender = sender
    self.subject = subject
    self.total = random.randint(1, 100)
    self.index = random.randint(1, self.total)
    self.size = random.randint(0,59)
    self.size_units = random.choice(['minutes', 'seconds'])

  def OnActivate(self, message, auto_focus):
    print self.target
    print self.combo
    return True

  def OnMoreInfo(self, message):
    # first say the target
    t = Output.Packet(self, message, Output.ACTIVE_CTRL)
    t.AddMessage(sound=SOUND%self.target)
    self.Output(self, t)

    # wait for a few moments before speaking again
    time.sleep(DELAY)

    # now send the simultaneous speech
    packets = []
    if 1 in self.combo or 2 in self.combo:
      content = Output.Packet(self, message, Output.ACTIVE_CTRL)
      if 1 in self.combo:
        print 'sender:', self.sender
        print 'subject:', self.subject
        content.AddMessage(speech='%s. %s' % (self.sender, self.subject),
                           person=Output.CONTENT)
      if 2 in self.combo:
        print 'index:', self.index
        print 'total:', self.total
        content.AddMessage(speech='message %d of %d' % (self.index,
                                                        self.total),
                           person=Output.SUMMARY)
      packets.append(content)
    if 3 in self.combo:
      print 'search:', self.sender[0]
      echo = Output.Packet(self, message, Output.NARRATOR)
      echo.AddMessage(speech=self.sender[0], letters=True,
                      person=Output.CONTENT)
      packets.append(echo)
    if 4 in self.combo:
      print 'length:', self.size
      print 'units:', self.size_units
      preview = Output.Packet(self, message, Output.ACTIVE_PROG)
      preview.AddMessage(speech='%d %s of text' % (self.size, self.size_units),
                         person=Output.CONTENT)
      packets.append(preview)

    self.Output(self, packets)
    print '======', self.target, self.combo

class Practice(Task.FormFill):
  Name = 'practice'
  Permanence = Task.NO_START|Task.NO_END

  def OnInit(self):
    for m in practice_msgs:
      t = Trial(self, None)
      t.init(*m)
      self.AddField(t)

class Trials(Task.FormFill):
  Name = 'trials'
  Permanence = Task.NO_START|Task.NO_END

  def OnInit(self):
    for m in trial_msgs:
      t = Trial(self, None)
      t.init(*m)
      self.AddField(t)

Tasks = [Practice, Trials]
AutoTasks = []
