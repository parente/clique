'''
Defines the manager for the output engine. All output messages pass through
here.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import pySonic, pyTTS
import weakref, time
import Speaker, Group
import Constants, Messages, Storage
import Interface, Support, Config, Input

class Pipe(object):
  '''
  Acts as a segment of a pipeline for message packets flowing out of the system.
  Weak references are used here because the parent maintains a strong reference
  to this object.

  @ivar parent: Next segment in the pipeline
  @type parent: weakref.proxy for L{Output.Manager.Pipe}
  '''
  def __init__(self, parent):
    self.parent = weakref.proxy(parent)

  def Output(self, source, packets):
    '''
    Forwards requests for audio ouput towards the output manager.

    @param source: Object that called this output method
    @type source: object
    @param packets: Packets to output
    @type packets: tuple or single L{Output.Messages.OutboundPacket}
    '''
    self.parent.Output(self, packets)

class Manager(Input.Pipe):
  '''
  Public interface to the audio output system. Directs output messages to the
  proper group.

  @ivar last_focus: Last object to have the focus before the memory menu was
      started
  @type last_focus: object
  @ivar last_word: Last word spoken in the main content stream and its start
    and end indices in the stream
  @type last_word: 3-tuple of (integer, integer, string)
  @ivar remember: Is the manager remember all content related speech?
  @type remember: boolean
  @ivar world: Virtual audiospace
  @type world: pySonic.World
  @ivar groups: Group objects keyed by ID
  @type groups: dictionary of L{Worker.Worker}
  @ivar history: Manages a queue of past messages
  @type history: L{Storage.HistoryRing}
  @ivar memory: Manages long term memory
  @type memory: L{Storage.MemoryTimer}
  @ivar speakers: All non-looping players and speakers
  @type speakers: tuple of L{Speaker.Players}
  @ivar LastEventTime: Time of the last output event referenced by some groups
      to know when to speak
  @type LastEventTime: float
  '''
  def __init__(self, im):
    '''
    Initializes an instance. Creates speakers and gives them to groups.

    @param im: Reference to the input manager and its message queue
    @type im: L{Input.Manager}
    '''
    super(Manager, self).__init__()
    # initialize variables related to long and short term memory
    self.remember = False
    self.last_word = (-1, -1, None)
    self.memory = Storage.MemoryBuffer()
    self.last_focus = None
    self.LastEventTime = time.time()
    # attach to the top of the input pipeline
    im.FocusNow(self)
    # load all TTS voices
    self.PrecacheVoices()
    # initialize the history
    self.history = Storage.HistoryRing(Constants.HISTORY_SIZE)
    # initialize our audio output library
    self.world = pySonic.World()
    self.world.MasterVolume = Config.master_volume
    # most soundcards don't support EAX reverb, but try anyways
    try:
      self.world.Reverb.SetPreset('room')
    except pySonic.FMODError:
      print 'no reverb effects available'

    # active task speakers
    content = Speaker.Speaker(Constants.CONTENT_VOICE,
                              speech_pos=Constants.CENTER,
                              sound_pos=Constants.CENTER_OFFSET,
                              sound_vol='content_sound',
                              speech_vol='content_voice')
    summary = Speaker.Speaker(Constants.SUMMARY_VOICE,
                              speech_pos=Constants.FRONT_LEFT,
                              sound_pos=Constants.FRONT_LEFT_OFFSET,
                              delay=0.3,
                              sound_vol='summary_sound',
                              speech_vol='summary_voice')
    # register for speech stream events on the content speaker
    content.SetObserver(self)
    # ubiquitous narrator speaker and player
    narrator = Speaker.Speaker(Constants.NARRATOR_VOICE,
                               speech_pos=Constants.FRONT_RIGHT,
                               sound_pos=Constants.FRONT_RIGHT_OFFSET,
                               delay=0.6,
                               sound_vol='narrator_sound',
                               speech_vol='narrator_voice')
    # related task speaker and player
    related = Speaker.Speaker(Constants.RELATED_VOICE,
                              speech_pos=Constants.LEFT,
                              sound_pos=Constants.LEFT_OFFSET,
                              delay=0.7,
                              sound_vol='related_sound',
                              speech_vol='related_voice')
    # unrelated task speaker and player
    outside = Speaker.Speaker(Constants.OUTSIDE_VOICE,
                              speech_pos=Constants.RIGHT,
                              sound_pos=Constants.RIGHT_OFFSET,
                              delay=0.7,
                              sound_vol='unrelated_sound',
                              speech_vol='unrelated_voice')
    # context change player, looping player, intermittent player, and ambience
    # pool
    change = Speaker.Player(sound_vol='change_sound')
    loop = Speaker.Player(sound_vol='looping_sound', looping=True)
    inter = Speaker.Intermittent(sound_vol='inter_sound')
    ambient = [Speaker.Ambience(max_vol='ambient_sound'),
               Speaker.Ambience(max_vol='ambient_sound')]

    # label all speakers
    narrator_group = {Constants.CONTENT: narrator}
    active_group = {Constants.CONTENT: content, Constants.SUMMARY: summary}
    inactive_group = {Constants.ACTIVE_PROG: related,
                      Constants.INACTIVE_PROG: outside}
    context_group = {Constants.CONTEXT: change, Constants.LOOPING: loop,
                     Constants.AMBIENCE: ambient, Constants.INTERMITTENT: inter}

    # create all groups
    self.groups = {}
    g = Group.ActiveGroup(self, narrator_group)
    self.groups[Constants.NARRATOR] = g
    g = Group.ActiveGroup(self, active_group)
    self.groups[Constants.ACTIVE_CTRL] = g
    g = Group.InactiveGroup(self, inactive_group)
    self.groups[Constants.ACTIVE_PROG] = g
    self.groups[Constants.INACTIVE_PROG] = g
    g = Group.ContextGroup(self, context_group)
    self.groups[Constants.CONTEXT] = g

    # store speakers so we can tell when they are quiet
    self.speakers = (narrator, content, summary, related, outside, change)

  def PrecacheVoices(self):
    '''
    Have all voices used speak an empty string to get them into the OS memory or
    disk cache. Improves performance on first speak.
    '''
    if Config.precache_voices:
      print 'precaching voices'
      tts = pyTTS.Create(output=False)
      for v in Constants.CACHE_VOICES:
        tts.Voice = v
        tts.Speak('the quick brown fox')
      print 'finished precaching voices'

  def Destroy(self):
    '''Stop all group threads.'''
    for g in self.groups.values():
      g.Destroy()

  def Output(self, source, packets):
    '''
    Directs an output request to the proper group. Silences other groups in
    some cases.

    @param source: Object that called this output method
    @type source: L{Output.Manager.Pipe}
    @param packets: Packets to output
    @type packets: L{Messages.OutboundPacket} or tuple of same
    '''
    try:
      len(packets)
    except:
      packets = (packets,)
    for p in packets:
      if p is None: continue
      # stamp the time the packet was received
      p.StampTime()
      # silence groups that are not recipients of the packet
      if p.Size > 0:
        self.Interrupt(p.Group)
      # get the group and dispatch
      g = self.groups[p.Group]
      g.Play(p)

  def PutHistory(self, packet):
    '''
    Adds a packet to the history. Unprepares the packet first to avoid
    storing pre-rendered speech for long periods of time.

    @param packet: Packet to retain
    @type packet: L{Output.Messages.OutboundPacket}
    '''
    packet.Unprepare()
    self.history.Push(packet)

  def IsSilent(self):
    '''
    @return: Are all non-looping speakers silent?
    @rtype: boolean
    '''
    for s in self.speakers:
      if s.IsPlaying(): return False
    return True

  def Interrupt(self, group=None):
    '''
    Silences groups that are being interrupted by the group that now has the
    floor.

    @param group: Group that has the floor or None to silence all
    @type group: integer
    '''
    if group is None or group == Constants.CONTEXT:
      self.groups[Constants.ACTIVE_CTRL].Stop()
      self.groups[Constants.ACTIVE_PROG].Stop()
      self.groups[Constants.INACTIVE_PROG].Stop()
      self.groups[Constants.NARRATOR].Stop()
    elif group == Constants.ACTIVE_CTRL:
      self.groups[Constants.ACTIVE_PROG].Stop()
      self.groups[Constants.INACTIVE_PROG].Stop()

  def IsMenuActive(self):
    '''
    @return: Is the memory chooser active?
    @rtype: boolean
    '''
    return self.last_focus is not None

  def OnIncRate(self, message):
    '''
    Increases the speech rate for all speakers.

    @param message: Input message that triggered this action
    @type message: L{Input.Messages.InboundMessage}
    '''
    if Config.speech_rate == 9:
      bound = 'last'
    else:
      bound = None
    Config.speech_rate = min(Config.speech_rate+1, 9)
    value = (Config.speech_rate+1)*10
    p = self.OutSetting(message, '%d%% speech rate', value, bound)
    self.Output(self, p)

  def OnDecRate(self, message):
    '''
    Decreases the speech rate for all speakers.

    @param message: Input message that triggered this action
    @type message: L{Input.Messages.InboundMessage}
    '''
    if Config.speech_rate == 0:
      bound = 'first'
    else:
      bound = None
    Config.speech_rate = max(Config.speech_rate-1, 0)
    value = (Config.speech_rate+1)*10
    p = self.OutSetting(message, '%d%% speech rate', value, bound)
    self.Output(self, p)

  def OnIncVolume(self, message):
    '''
    Increases the the volume for all audio output.

    @param message: Input message that triggered this action
    @type message: L{Input.Messages.InboundMessage}
    '''
    if Config.master_volume == 255:
      bound = 'last'
    else:
      bound = None
    Config.master_volume = min(Config.master_volume+15, 255)
    self.world.MasterVolume = Config.master_volume
    value = int((Config.master_volume/255.0)*100)
    p = self.OutSetting(message, '%d%% volume', value, bound)
    self.Output(self, p)

  def OnDecVolume(self, message):
    '''
    Decreases the volume for all audio output.

    @param message: Input message that triggered this action
    @type message: L{Input.Messages.InboundMessage}
    '''
    if Config.master_volume == 0:
      bound = 'first'
    else:
      bound = None
    Config.master_volume = max(Config.master_volume-15, 0)
    self.world.MasterVolume = Config.master_volume
    value = int((Config.master_volume/255.0)*100)
    p = self.OutSetting(message, '%d%% volume', value, bound)
    self.Output(self, p)

  def OnChooseMemory(self, message):
    '''
    Creates a L{View.Control.List} object with L{memory} as its model to allow
    the user to browse the contents of long term memory.

    Plays OutChooseMemory or OutRefuseMemory.

    @param message: Input message that triggered the interruption
    @type message: L{Input.Messages.InboundMessage}
    '''
    # don't nest menus
    if self.IsMenuActive():
      return
    elif self.memory.GetItemCount() == 0:
      p = self.OutRefuseMemory(message)
      self.Output(self, p)
      return
    # have to import View here because of crazy circular references
    import View

    # create a list with the memory storage as model
    plist = View.Control.List(self, self.memory, name='long term memory')
    p = self.OutIntroduction(message, False)
    self.Output(self, p)
    self.last_focus = self.focus
    self.ChangeFocus(plist, message, False)

  def OnDoThat(self, message):
    '''
    Selects the currently selected memory chunk and sends it to the last 
    focused L{View} to process.

    @param message: Input message that triggered the interruption
    @type message: L{Input.Messages.InboundMessage}
    '''
    if message.Press:
      man = Input.Manager()
      msg = Input.TextMessage(Constants.MEMORY_INSERT,
                              self.memory.GetSelectedName())
      msg.RouteThrough(self.last_focus)
      man.AddMessage(msg)

  def OnEscape(self, message):
    '''
    Gives the focus back to the L{View.Task} object that had it before the
    chooser started.
    
    @param message: Input message that triggered the interruption
    @type message: L{Input.Messages.InboundMessage}
    '''
    #restore old focus
    self.ChangeFocus(self.last_focus, message, False)
    self.last_focus = None

  def OnShutUp(self, message):
    '''
    Handle an input message requesting all output, except ambient sound, to
    stop playing, but only when the shut up command is first given.

    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    if message.Press:
      self.Interrupt(None)

  def OnInformSystemShutdown(self, message):
    '''
    Handle an input message requesting the termination of Clique by playing
    the shutdown sound.

    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    # save all log data
    Config.save_log()
    if Config.fast_shutdown:
      # @todo: temporary for fast shutdown
      Input.Manager().Destroy()
      self.Destroy()
    else:
      # play the shutdown sound
      p = Messages.OutboundPacket(self, message, Constants.CONTEXT, True,
                                  'shutdown')
      p.AddMessage(sound=Interface.ISound(self).Action('system shutdown'))
      self.Output(self, p)
      
  def OnInformSystemStartup(self, message):
    '''
    Called when the system first starts up and becomes interactive.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # play the startup sound
    p = Messages.OutboundPacket(self, message, Constants.CONTEXT, True,
                                'startup')
    p.AddMessage(sound=Interface.ISound(self).Action('system startup'))
    self.Output(self, p)

  def OnSayDone(self, message):
    '''
    Receives a stream done event. Resets the last word spoken.

    @param message: Message that caused this event handler to fire
    @type message: L{Output.Messages.StreamMessage}
    '''
    self.last_word = (-1, -1, self.last_word[2])

  def OnSayWord(self, message):
    '''
    Receives words spoken by the content speaker. Adds them to a temporary
    buffer whenever remembering is active.

    @param message: Message that caused this event handler to fire
    @type message: L{Output.Messages.StreamMessage}
    '''
    # compute the word being said
    tp = message.TruePosition
    text = message.Text
    s = text.rfind(' ', 0, tp)
    e = text.find(' ', tp)
    if s == -1: s = None
    if e == -1: e = None
    # if the start and end of the word are the same as the last word, ignore it
    #if self.last_word[0] == s and self.last_word[1] == e:
    #  return
    self.last_word = (s, e, text[s:e])
    # store it to working memory
    if self.remember:
      self.memory.AddToWorking(self.last_word)

  def OnRemember(self, message):
    '''
    Starts or stops capturing all spoken words to a temporary buffer. Joins the
    buffer into a string and places it in long-term memory when stopping. Adds
    the last word spoken in the active stream to working memory if the stream
    is still being spoken.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    self.remember = message.Press
    if not self.remember:
      # add contents of working memory to long term storage
      self.memory.AddToLongTerm()
    elif self.last_word[2] is not None:
      # add the last word said to working memory immediately
      #self.memory.AddToWorking(self.last_word[2])
      pass
    p = self.OutRemember(message)
    self.Output(self, p)

  def OnReplayHistory(self, message):
    '''
    Reads through the entire history until stopped.

    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = self.OutHistory(message)
    self.Output(self, p)

  def OnPacketDone(self, message):
    '''
    Handle an event when a packet has finished playing succesfully by either
    adding a startup message or shutting down the output system.

    @param message: Input message that caused the creation of the packet
    @type message: L{Messages.PacketMessage}
    '''
    if message.Packet.Name == 'startup':
      Input.Manager().AddStartupMessage()
    elif message.Packet.Name == 'shutdown':
      Input.Manager().Destroy()
      self.Destroy()
    elif message.Packet.Name == 'history':
      p = self.OutHistory(message)
      self.Output(self, p)

  def OnPacketPreempt(self, message):
    '''
    Resets the generator responsible for giving information about the current
    selection if any user action preempts the last detail.

    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    '''
    if message.Packet.Name != 'history':
      self.OutHistory_gen(message, reset_gen=True)

  def OnChooseTask(self, message):
    '''
    Reports that the task menu is not available.

    Calls OutRefuseTask.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = self.OutRefuseTask(message)
    self.Output(self, p)

  def OnChooseProgram(self, message):
    '''
    Reports that the program menu is not available.

    Calls OutRefuseProgram.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = self.OutRefuseProgram(message)
    self.Output(self, p)

  def OutRemember(self, message):
    '''
    Plays a sound indicating if the system is starting or stopping remembering
    everything that is being said.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Messages.OutboundPacket(self, message, group=Constants.NARRATOR)
    p.AddMessage(sound=Interface.ISound(self).Action('remember'))
    return p

  def OutSetting(self, message, text, value, bound):
    '''
    Plays speech indicating a current volume or speech rate setting. Plays
    a boundary sound if already at the max/min volume or rate.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text describing the setting with one %d field for the value
      percentage
    @type text: string
    @param value: Current setting value as a percentage
    @type value: integer
    @param: Type of boundary reached
    @type: string or None
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Messages.OutboundPacket(self, message)
    if bound is not None:
      p.AddMessage(sound=Interface.ISound(self).State(bound),
                   person=Constants.SUMMARY)
    p.AddMessage(speech=text % value)
    return p

  def OutHistory(self, message):
    '''
    Starts the inactive group reading packets from the history.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = self.OutHistory_gen(message)
    if p is None:
      p = Messages.OutboundPacket(self, message, Constants.ACTIVE_PROG)
      p.AddMessage(sound=Interface.ISound(self).State('last'))
    return p

  @Support.generator_method('Manager')
  def OutHistory_gen(self, message):
    '''
    Ouputs the next oldest packet from the history.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    start_mark = time.time()
    last_mark = start_mark
    # iterate through the packet history
    for packet in self.history:
      # compute time since last minute mark
      if last_mark - packet.Time > 60:
        last_mark = packet.Time
        p = Messages.OutboundPacket(self, message, Constants.ACTIVE_PROG, True,
                                    'history')
        p.AddMessage(speech='%d minutes ago' % (int(start_mark-packet.Time)/60),
                     sound=Interface.ISound(self).Action('previous'))
        yield p
      else:
        p = Messages.OutboundPacket(self, message, Constants.ACTIVE_PROG, True,
                                    'history')
        # put a bit of a pause between items
        p.AddMessage(speech=', , ')
        yield p
      # re-intialize the packet with history metadata
      packet.Initialize(self, message, packet.Group, True, 'history')
      yield packet

  def OutIntroduction(self, message, auto_focus):
    '''
    Introduces the long term memory menu.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Packet of information to be output
    @rtype: tuple of L{Output.Messages.OutboundPacket}
    '''
    # silence any program ambience and start the memory loop
    p = Messages.OutboundPacket(self, message, Constants.CONTEXT)
    p.AddMessage(sound=Interface.ISound(self).Action('start'))
    p.AddMessage(sound=Interface.ISound(self).Identity('task'),
                 person=Constants.LOOPING)
    return p

  def OutRefuseTask(self, message):
    '''
    Outputs the refuse sound and a message explaining that the user must
    quit the memory menu before accessing the task menu.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = Messages.OutboundPacket(self, message)
    p.AddMessage(speech='You must exit the memory menu before choosing a task.',
                 person=Constants.SUMMARY,
                 sound=Interface.ISound(self).Warn('refuse'))
    return p

  def OutRefuseProgram(self, message):
    '''
    Outputs the refuse sound and a message explaining that the user must
    quit the memory menu before accessing the program menu.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = Messages.OutboundPacket(self, message)
    p.AddMessage(speech='You must exit the memory menu before choosing a program.',
                 person=Constants.SUMMARY,
                 sound=Interface.ISound(self).Warn('refuse'))
    return p

  def OutRefuseMemory(self, message):
    '''
    Outputs the refuse sound and a message explaining that the user must put
    items in memory before accessing the memory menu.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = Messages.OutboundPacket(self, message)
    p.AddMessage(speech='Long term memory is empty.',
                 person=Constants.SUMMARY,
                 sound=Interface.ISound(self).Warn('refuse'))
    return p

if __name__ == '__main__':
  pass
