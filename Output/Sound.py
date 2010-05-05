'''
Defines interfaces for mapping program objects to audio icon files on disk.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from protocols import advise, Adapter
from Interface import ISound
from Identity import IdentityManager
import Manager, Messages, Constants
import View

class ControlAsISound(Adapter):
  '''
  Adapts any L{View.Control} to the ISound interface. Provides basic state and
  navigation sounds.

  @ivar states: State to sound map
  @type states: dictionary
  @ivar actions: Action to sound map
  @type actions: dictionary
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Control.Base])

  def __init__(self, subject):
    self.subject = subject
    self.roles = {}
    self.states = {'navigable' : 'tom_hit',
                   'first' : 'timpani_hit',
                   'last' : 'timpani_two_hits',
                   'missing' : 'tom_roll'}
    self.actions = {'next' : 'flute_sync_down',
                    'previous' : 'flute_sync_up',
                    'wrap' : 'flute_sync',
                    'delete' : 'flute_discord',
                    'join-word' : 'flute_two_up',
                    'split-word' : 'flute_two_down',
                    'join-chunk' : 'flute_chord_up',
                    'split-chunk' : 'flute_chord_down',
                    'search' : 'swoosh'}
    self.warnings = {'clash' : 'baritone_honk',
                     'refuse' : 'baritone_blues'}

  def Role(self, name):
    try:
      return self.roles[name]+'.wav'
    except TypeError:
      return None

  def State(self, name):
    try:
      return self.states[name]+'.wav'
    except TypeError:
      return None

  def Action(self, name):
    try:
      return self.actions[name]+'.wav'
    except TypeError:
      return None
    
  def Warn(self, name):
    try:
      return self.warnings[name]+'.wav'
    except TypeError:
      return None

class TextReadingAsISound(ControlAsISound):
  '''
  Adapts a read-only text view to the ISound interface. Provides a start sound.
  '''
  advise(instancesProvide=[ISound],asAdapterForTypes=[View.Control.TextReading])

  def __init__(self, *args, **kwargs):
    ControlAsISound.__init__(self, *args, **kwargs)
    self.actions['start'] = 'paper_rustle'
    
class DocumentReadingAsISound(TextReadingAsISound):
  '''
  Adapts a read-only document view to the ISound interface. Removes the next
  and previous chunk sounds since document chunk boundaries can appear in
  mid-sentence (e.g. a hypertext link in the middle of a sentence).
  '''
  advise(instancesProvide=[ISound], 
         asAdapterForTypes=[View.Control.DocumentReading])

  def __init__(self, *args, **kwargs):
    TextReadingAsISound.__init__(self, *args, **kwargs)
    self.actions['next'] = None
    self.actions['previous'] = None
    self.roles.update({'list item' : 'card_deck_ruffle',
                       'link' : 'zap',
                       'h1' : 'marching_footsteps',
                       'h2' : 'marching_footsteps',
                       'h3' : 'marching_footsteps',
                       'h4' : 'marching_footsteps',
                       'h5' : 'marching_footsteps',
                       'h6' : 'marching_footsteps',
                       'editable text' : 'paper_rustle',
                       'document' : 'paper_rustle'})

class TextEntryAsISound(ControlAsISound):
  '''
  Adapts a editable text view to the ISound interface. Provides a start sound.
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Control.TextEntry])

  def __init__(self, *args, **kwargs):
    ControlAsISound.__init__(self, *args, **kwargs)
    self.actions['start'] = 'typing_short'

class ListAsISound(ControlAsISound):
  '''
  Adapts a list view to the ISound interface. Provides a start sound.
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Control.List])

  def __init__(self, *args, **kwargs):
    ControlAsISound.__init__(self, *args, **kwargs)
    self.actions['start'] = 'card_deck_ruffle'

class TreeAsISound(ControlAsISound):
  '''
  Adapts a tree view to the ISound interface. Provides a start sound.
  '''
  advise(instancesProvide=[ISound], 
         asAdapterForTypes=[View.Control.Tree, View.Control.StridedList])

  def __init__(self, *args, **kwargs):
    ControlAsISound.__init__(self, *args, **kwargs)
    self.actions['start'] = 'wind_leaves'

class TaskAsISound(Adapter):
  '''
  Adapts any L{View.Task.Base} to the ISound interface. Provides basic state and
  warning sounds. No timbre is specified for actions.

  @ivar states: State to sound map
  @type states: dictionary
  @ivar actions: Action to sound map
  @type actions: dictionary
  @ivar warnings: Warning to sound map
  @type warnings: dictionary
  @ivar timbre: Name of the timbre to apply to actions
  @type timbre: string
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Task.Base])

  def __init__(self, subject):
    self.subject = subject
    self.states = {'last' : 'timpani_two_hits',
                   'waiting' : 'fading_woodblock'}
    self.actions = {'start' : 'rising_melody',
                    'resume' : 'average_melody',
                    'complete' : 'falling_major_melody',
                    'cancel' : 'falling_minor_melody',
                    'wrap' : 'sync'}
    self.warnings = {'refuse' : 'baritone_blues'}
    self.timbre = 'piano'

  def State(self, name):
    try:
      return self.states[name]+'.wav'
    except TypeError:
      return None

  def Action(self, name):
    try:
      return self.timbre+'_'+self.actions[name]+'.wav'
    except TypeError:
      return None

  def Identity(self, name=''):
    try:
      return IdentityManager.GetTaskIdentity(self.subject)
    except TypeError:
      return None

  def Warn(self, name):
    try:
      return self.warnings[name]+'.wav'
    except TypeError:
      return None

class FormFillAsISound(TaskAsISound):
  '''
  Adapts a form fill task to the ISound interface. Provides an action timbre.
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Task.FormFill])

  def __init__(self, *args, **kwargs):
    TaskAsISound.__init__(self, *args, **kwargs)
    self.timbre = 'guitar'

class LinkedBrowsingAsISound(TaskAsISound):
  '''
  Adapts a linked browsing task to the ISound interface. Provides an action
  timbre.
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Task.LinkedBrowsing])

  def __init__(self, *args, **kwargs):
    TaskAsISound.__init__(self, *args, **kwargs)
    self.timbre = 'banjo'

class DiskBrowsingAsISound(TaskAsISound):
  '''
  Adapts a disk browsing task to the ISound interface. Provides an action
  timbre.
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Task.FolderBrowsing])

  def __init__(self, *args, **kwargs):
    TaskAsISound.__init__(self, *args, **kwargs)
    self.timbre = 'steel_drum'

class ProgramAsISound(TaskAsISound):
  '''
  Adapts a L{View.Task.Program} to the ISound interface. Provides an action
  timbre.
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Task.Program])

  def __init__(self, *args, **kwargs):
    TaskAsISound.__init__(self, *args, **kwargs)
    self.timbre = 'kalimba'

  def Identity(self, name=''):
    if name == 'container':
      return IdentityManager.GetProgramIdentity(self.subject)
    elif name == 'task':
      return 'jungle_beat.wav'

class ProgramManagerAsISound(TaskAsISound):
  '''
  Adapts a L{View.Task.Manager} to the ISound interface. Provides an action
  timbre.
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[View.Task.ProgramManager])
    
  def Identity(self, name=''):
    return 'hiphop_beat.wav'

class OutboundMessageAsISound(Adapter):
  '''
  Adapts a L{Output.Messages.OutboundMessage} to the ISound interface.
  Kind of strange, but needed to provide the misspelled state.

  @ivar states: State to sound map
  @type states: dictionary
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[Messages.OutboundMessage])

  def __init__(self, subject):
    self.subject = subject
    self.states = {'misspelled' : 'tambourine'}

  def State(self, name):
    return self.states[name]+'.wav'

class OutputManagerAsISound(Adapter):
  '''
  Adapts the L{Output.Manager.Manager} to the ISound interface. Kind of strange,
  but needed to report system startup and history navigation sounds.

  @ivar states: State to sound map
  @type states: dictionary
  @ivar actions: Action to sound map
  @type actions: dictionary
  '''
  advise(instancesProvide=[ISound], asAdapterForTypes=[Manager.Manager])

  def __init__(self, subject):
    self.subject = subject
    self.states = {'last' : 'timpani_two_hits',
                   'first': 'timpani_hit'}
    self.actions = {'system startup' : 'synth_welcome_melody',
                    'system shutdown' : 'synth_goodbye_melody',
                    'start' : 'honky_piano_rising_melody',
                    'complete' : 'honky_piano_falling_major_melody',
                    'cancel' : 'honky_piano_falling_minor_melody',
                    'previous' : 'tape_rewind',
                    'remember' : 'squeak'}
    self.warnings = {'refuse' : 'baritone_blues'}

  def State(self, name):
    try:
      return self.states[name]+'.wav'
    except TypeError:
      return None

  def Action(self, name):
    try:
      return self.actions[name]+'.wav'
    except TypeError:
      return None
  
  def Identity(self, name=''):
    return 'mambo_beat.wav'

  def Warn(self, name):
    try:
      return self.warnings[name]+'.wav'
    except TypeError:
      return None
