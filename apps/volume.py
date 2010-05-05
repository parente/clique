'''
Volume control

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import random
import Config
import Support
import UIA, Output, View
from View import Task

content_sound = 'squeak.wav'
summary_sound = 'tom_hit.wav'
narrator_sound = 'swoosh.wav'
related_sound = 'paper_rustle.wav'
unrelated_sound = 'paper_rustle.wav'
change_sound = 'piano_rising_melody.wav'
inter_sound = 'identity/harbor/dolphin.wav'
looping_sound = 'jungle_beat.wav'
ambient_sound = 'identity/crickets.wav'

class Main(UIA.Macro):
  def Sequence(self):
    yield True

class Volume(View.Base):
  def init(self, attr_name, person, group):
    self.attr_name = attr_name
    self.person = person
    self.group = group
    return self

  def OnActivate(self, message, auto_focus):
    if auto_focus:
      message = None
    p = self.OutIntroduction(message)
    self.Output(self, p)
    return True

  def _OutCurrent(self, message):
    '''Override in subclass to output info about this volume control.'''
    return

  def OnMoreInfo(self, message):
    '''
    Outputs speech and sound on most channels as a test.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    # make packets for all speakers
    p1 = Output.Packet(self, message)
    p1.AddMessage(speech='content voice', sound=content_sound, person=Output.CONTENT)
    p1.AddMessage(speech='summary voice', sound=summary_sound, person=Output.SUMMARY)
    p2 = Output.Packet(self, message, Output.NARRATOR)
    p2.AddMessage(speech='narrator voice', sound=narrator_sound)
    p3 = Output.Packet(self, None, Output.ACTIVE_PROG)                     
    p3.AddMessage(speech='related voice', sound=related_sound)
    p4 = Output.Packet(self, None, Output.INACTIVE_PROG)
    p4.AddMessage(speech='unrelated voice', sound=unrelated_sound)
    self.Output(self, (p1, p2, p3, p4))

  def OutIntroduction(self, message):
    p = Output.Packet(self, message, self.group)
    p.AddMessage(speech=' '.join(self.attr_name.split('_')), person=self.person)
    return p

class Speaker(Volume):
  def _OutCurrent(self, message):
    vol = getattr(Config, self.attr_name)
    value = int((vol/255.0)*100)
    p = Output.Packet(self, message, self.group)
    p.AddMessage(speech='%d percent volume' % value, person=self.person)
    return p
  
  def OnNextMid(self, message):
    vol = getattr(Config, self.attr_name)
    vol = min(vol+15, 255)
    setattr(Config, self.attr_name, vol)

    p = self._OutCurrent(message)
    self.Output(self, p)

  def OnPrevMid(self, message):
    vol = getattr(Config, self.attr_name)
    vol = max(vol-15, 0)
    setattr(Config, self.attr_name, vol)

    p = self._OutCurrent(message)
    self.Output(self, p)

class Player(Volume):
  def _OutCurrent(self, message):
    sound = globals()[self.attr_name]
    p1 = Output.Packet(self, message, self.group)
    p1.AddMessage(sound=sound, person=self.person, refresh=True)
    vol = getattr(Config, self.attr_name)
    value = int((vol/255.0)*100)
    if self.attr_name.find('related') < 0:
      p2 = Output.Packet(self, None)
      p2.AddMessage(speech = "%d percent volume" % value)
      return p1, p2
    return p1
  
  def OnNextMid(self, message):
    vol = getattr(Config, self.attr_name)
    vol = min(vol+15, 255)
    setattr(Config, self.attr_name, vol)

    p = self._OutCurrent(message)
    self.Output(self, p)

  def OnPrevMid(self, message):
    vol = getattr(Config, self.attr_name)
    vol = max(vol-15, 0)
    setattr(Config, self.attr_name, vol)
    value = int((vol/255.0)*100)

    p = self._OutCurrent(message)
    self.Output(self, p)

class Context(Player):
  def OutIntroduction(self, message):
    p = Output.Packet(self, message)
    p.AddMessage(speech=' '.join(self.attr_name.split('_')))
    return p
 
class VolumeControl(Task.FormFill):
  Name = 'volume control'
  Permanence = Task.NO_START|Task.NO_END
  
  def OnInit(self):
    sp = [Speaker(self, None).init('content_voice', Output.CONTENT, Output.ACTIVE_CTRL),
          Speaker(self, None).init('summary_voice', Output.SUMMARY, Output.ACTIVE_CTRL),
          Speaker(self, None).init('narrator_voice', Output.CONTENT, Output.NARRATOR),
          Speaker(self, None).init('related_voice', Output.CONTENT, Output.ACTIVE_PROG),
          Speaker(self, None).init('unrelated_voice', Output.CONTENT, Output.INACTIVE_PROG),
          Player(self, None).init('content_sound', Output.CONTENT, Output.ACTIVE_CTRL),
          Player(self, None).init('summary_sound', Output.SUMMARY, Output.ACTIVE_CTRL),
          Player(self, None).init('narrator_sound', Output.CONTENT, Output.NARRATOR),
          Player(self, None).init('related_sound', Output.CONTENT, Output.ACTIVE_PROG),
          Player(self, None).init('unrelated_sound', Output.CONTENT, Output.INACTIVE_PROG),
          Context(self, None).init('change_sound', Output.CONTENT, Output.CONTEXT),
          Context(self, None).init('inter_sound', Output.INTERMITTENT, Output.CONTEXT),
          Context(self, None).init('looping_sound', Output.LOOPING, Output.CONTEXT),
          Context(self, None).init('ambient_sound', Output.AMBIENCE, Output.CONTEXT)]
          
    map(self.AddField, sp)

Tasks = [VolumeControl]
AutoTasks = []
