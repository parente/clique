'''
Defines classes responsible for generating and playing audio.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import time, threading, Queue, os, random
import pythoncom, pySonic, pyTTS
import Storage, Worker, Constants
import Input, Support, Config

class Factory(object):
  '''
  Base audio output class that returns empty sounds that can be played, but make
  no noise.
  '''
  def Create(self, message):
    '''
    Virtual method. Produce audio output based on the output message.

    @param message: Message containing information about the audio to generate
    @type message: L{Messages.OutboundMessage}
    @return: Audio data to output
    @rtype: pySonic.Sound
    '''
    return pySonic.Sound()

class SoundFactory(Factory):
  '''
  Factory object that returns playable audio objects for sounds loaded from disk.
  '''
  def Create(self, message):
    '''
    Produce non-speech audio output based on the output message.

    @param message: Message containing information about the audio to generate
    @type message: L{Messages.OutboundMessage}
    @return: Audio data to output
    @rtype: pySonic.Sound
    '''
    if message.Sound is None:
      return pySonic.Sound()
    else:
      try:
        return pySonic.FileStream(os.path.join(Constants.SOUND_PATH,
                                  message.Sound),
                                  pySonic.Constants.FSOUND_HW3D)
      except pySonic.FMODError, e:
        if Config.show_text:
          print message.Sound, e
        # return a blank sound if the file was not found
        return pySonic.Sound()

class SpeechFactory(Factory):
  '''
  Factory object that returns playable audio objects for generated speech.

  @ivar tts: Text-to-speech synthesizer
  @type tts: pyTTS.?
  '''
  def __init__(self, voice):
    '''
    Initialize the object.

    @param voice: Name of the voice to use when generating speech
    @type voice: string
    '''
    self.tts = pyTTS.Create(output=False)
    self.tts.SetOutputFormat(16, 16, 1)
    self.tts.Voice = voice
    self.tts.Rate = Config.speech_rate

  def GetVoice(self):
    '''
    Gets the voice used by this speech factory.

    @return: Voice used by this factory
    @rtype: pyTTS voice object
    '''
    return self.tts.Voice
  Voice = property(GetVoice)

  def Create(self, message):
    '''
    Produce speech audio output based on the output message.

    @param message: Message containing information about the audio to generate
    @type message: L{Messages.OutboundMessage}
    @return: Audio data to output and events
    @rtype: 2-tuple of pySonic.Sound and L{Output.SpeechStream.Queue}
    '''
    events = None
    sound = pySonic.Sound()
    # only render if we actually have speech data
    if message.Speech is not None:
      # compute the xml flag
      xml = (message.IsXML and pyTTS.tts_is_xml) or \
            (not message.IsXML and pyTTS.tts_is_not_xml)
      try:
        # update the speech rate
        self.tts.Rate = Config.speech_rate
        # try to generate audio data
        stream, tts_events = self.tts.Speak(message.Speech, xml)
      except pythoncom.com_error:
        # ensure coinit called in this thread context and retry
        pythoncom.CoInitialize()
        return self.Create(message)
      except:
        return sound, events
      # get audio format info and wave data
      format = stream.Format.GetWaveFormatEx()
      data = stream.GetData()[int(-0.0125*self.tts.Rate+0.2):-1600]
      if len(data) > 0:
        # create the audio data as a sample so playback position is accurate
        sound = pySonic.MemorySample(data, format.Channels, format.BitsPerSample,
                        format.SamplesPerSec, pySonic.Constants.FSOUND_HW3D)
      # there might be events regardless of whether or not sound was made
      events = Storage.StreamQueue(tts_events, message, format.BitsPerSample/8)
    return sound, events

class Player(Worker.Worker):
  '''
  A virtual instrument capable of playing a single non-verbal sound at a time.

  @ivar sound_fac: Factory that produces sound audio
  @type sound_fac: L{SoundFactory}
  @ivar sound_src: Plays non-verbal audio
  @type sound_src: pySonic.Source
  @ivar sound_vol: Volume of the sound stream
  @type sound_vol: number
  @ivar sound_loop: Looping mode for the sound
  @type sound_loop: integer
  '''
  def __init__(self, sound_pos=(0,0,0), sound_vol=None, looping=False,
               autostart=True):
    '''
    Initialize an instance.

    @param sound_pos: Location of the sound stream in 3D space
    @type sound_pos: 3-tuple of number
    @param sound_vol: Volume of the sound stream
    @type sound_vol: number
    @param looping: Should the sound loop?
    @type looping: boolean
    @param autostart: Should the thread loop be started immediately?
    @type autostart: boolean
    '''
    super(Player, self).__init__()
    if sound_vol:
      self.sound_vol = sound_vol
    else:
      self.sound_vol = 'master_volume'
    if looping:
      self.sound_loop = pySonic.Constants.FSOUND_LOOP_NORMAL
    else:
      self.sound_loop = pySonic.Constants.FSOUND_LOOP_OFF

    # create a factory
    self.sound_fac = SoundFactory()
    # create a sound source
    self.sound_src = pySonic.Source()
    self.sound_src.Position = sound_pos
    # create the message queue
    self.incoming = Queue.Queue()
    # create room to save the last message processed
    self.last_message = Support.Null()
    # only start the thread loop if requested
    if autostart: self.start()

  def IsPlaying(self):
    '''
    @return: Is either the sound or speech source playing?
    @rtype: boolean
    '''
    return self.sound_src.IsPlaying()

  def IsLooping(self):
    '''
    @return: Is the sound looping?
    @rtype: boolean
    '''
    return ((self.sound_loop == pySonic.Constants.FSOUND_LOOP_NORMAL) and
           self.IsPlaying())

  def WaitForEvent(self):
    '''
    Wait for an event to occur.

    @return: Event objects or None if the thread dies
    @rtype: tuple
    '''
    while self.alive:
      try:
        # lock to prevent a preemption
        self.plock.acquire()
        # try to get an object and clear the preempt flag if we do
        mb = self.incoming.get(True, Constants.SPIN_DELAY)
        self.preempt.clear()
        self.plock.release()
        # return the packet and a new barrier
        return mb
      except Queue.Empty:
        # no packet available, release the preempt lock
        self.plock.release()
    # the thread is dead
    return None

  def HandleEvent(self, message, barrier):
    '''
    Create sound audio data and begin playback.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Barrier at which the speaker must arrive when it is done
    @type barrier: L{Worker.Barrier}
    @return: True to continue processing, False to wait for the next message
    @rtype: boolean
    '''
    # if we're a looping source, avoid playing the same looping sound again
    if (self.IsLooping() and self.last_message.Sound == message.Sound and
        not message.Refresh):
      return False
    # create and play the sound
    self.sound_src.Sound = self.sound_fac.Create(message)
    self.sound_src.Volume = getattr(Config, self.sound_vol)
    self.sound_src.LoopMode = self.sound_loop
    self.sound_src.Play()
    # save the last message
    self.last_message = message
    if Config.show_text and message.Sound is not None:
      print 'play:', message.Sound
    return True

  def WaitWhileProcessing(self, message, barrier):
    '''
    Check for preemption or thread death while playing.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Barrier at which the speaker must arrive when it is done
    @type barrier: L{Worker.Barrier}
    @return: True to continue processing, False to wait for the next message
    @rtype: boolean
    '''
    while self.alive:
      # wait unless signaled
      self.preempt.wait(Constants.SPIN_DELAY)
      # break if we've finished playing:
      if not self.IsPlaying() and not self.preempt.isSet():
        return True
      # break if preempted by another sound
      elif self.preempt.isSet():
        return False
    return False

  def CompleteEvent(self, message, barrier):
    '''
    Arrive at the barrier.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Barrier at which the speaker must arrive when it is done
    @type barrier: L{Worker.Barrier}
    '''
    # arrive at the barrier
    barrier.Arrive()
    self.SilenceAll()

  def SilenceAll(self):
    '''Stop the sound source from playing immediately.'''
    if self.sound_src.IsPlaying():
      self.sound_src.Stop()

  def Stop(self):
    '''
    Preempts playing audio and throws away waiting messages.
    '''
    # throw away queued audio and return to waiting state
    self.plock.acquire()
    self.incoming = Queue.Queue()
    self.preempt.set()
    self.SilenceAll()
    self.plock.release()

  def Play(self, message, barrier):
    '''
    Plays a message immediately, throwing away all queued messages.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Synchronization object for multiple speakers
    @type barrier: L{Worker.Barrier}
    '''
    self.plock.acquire()
    # throw away the queue
    self.incoming = Queue.Queue()
    self.incoming.put((message, barrier))
    self.preempt.set()
    self.plock.release()

  def PlayLater(self, message, barrier):
    '''
    Adds a message to the queue to be played later.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Synchronization object for multiple speakers
    @type barrier: L{Worker.Barrier}
    '''
    self.incoming.put((message, barrier))

class Speaker(Player):
  '''
  A virtual person capable of playing a single speech stream and a single sound
  simultaneously.

  @ivar speech_fac: Factory that produces speech audio
  @type speech_fac: L{SpeechFactory}
  @ivar speech_src: Speaks synthesized speech
  @type speech_src: pySonic.Source
  @ivar speech_vol: Volume of the speech stream
  @type speech_vol: number
  @ivar voice: Name of the voice to use for this speaker
  @type voice: string
  @ivar delay: Seconds to delay before starting output
  @type delay: float
  @ivar observer: Observer that will receive stream messages
  @type observer: L{Input.Pipe}
  '''
  def __init__(self, voice, speech_pos=(0,0,0), sound_pos=(0,0,0),
               speech_vol=None, sound_vol=None, delay=0.0, autostart=True):
    '''
    Stores speaker settings.

    @param voice: Name of the voice to use for speech synthesis
    @type voice: string
    @param speech_pos: Location of the speech stream in 3D space
    @type speech_pos: 3-tuple of number
    @param sound_pos: Location of the sound stream in 3D space
    @type sound_pos: 3-tuple of number
    @param sound_vol: Volume of the sound stream
    @type sound_vol: number
    @param speech_vol: Volume of the speech stream
    @type speech_vol: number
    @ivar delay: Seconds to delay before starting output
    @type delay: float
    @param autostart: Should the thread loop be started immediately?
    @type autostart: boolean
    '''
    super(Speaker, self).__init__(sound_pos, sound_vol, autostart=False)
    if speech_vol is not None:
      self.speech_vol = speech_vol
    else:
      self.speech_vol = 'master_volume'
    self.delay = delay

    # create factory
    self.speech_fac = SpeechFactory(voice)
    self.voice = voice

    # create a speech source
    self.speech_src = pySonic.Source()
    self.speech_src.Position = speech_pos

    # make room for a speech stream observer
    self.observer = None

    # start the thread loop if requested
    if autostart: self.start()

  def SetObserver(self, observer):
    '''
    Stores a single observer that will be notified about speech stream events.
    Only one observer is currently supported, but support for multiple observers
    could be added. This observer is notified indpendently of the source of the
    output message that triggered speech.

    @param observer: Observer that will receive stream messages
    @type observer: L{Input.Pipe}
    '''
    self.observer = observer

  def CloneSpeechFactory(self):
    '''
    Clones the speaker's speech factory. The result can be used to render speech
    outside of the speaker (e.g. to pre-render).

    @return: Clone of the speech factory
    @rtype: L{SpeechFactory}
    '''
    return SpeechFactory(self.speech_fac.Voice)

  def IsPlaying(self):
    '''
    @return: Is either the sound or speech source playing?
    @rtype: boolean
    '''
    return self.sound_src.IsPlaying() or self.speech_src.IsPlaying()

  def HandleEvent(self, message, barrier):
    '''
    Create speech and sound audio data, get speech stream events, and begin
    playback.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Barrier at which the speaker must arrive when it is done
    @type barrier: L{Worker.Barrier}
    @return: True to continue processing, False to wait for the next message
    @rtype: boolean
    '''
    super(Speaker, self).HandleEvent(message, barrier)
    # create speech and play it
    self.speech_src.Sound = message.Prepare(self.speech_fac)
    self.speech_src.Volume = getattr(Config, self.speech_vol)
    time.sleep(self.delay)
    self.speech_src.Play()
    if Config.show_text and message.Speech is not None:
      print 'say:', message.Speech
    return True

  def WaitWhileProcessing(self, message, barrier):
    '''
    Check for stream events or preemption while playing.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Barrier at which the speaker must arrive when it is done
    @type barrier: L{Worker.Barrier}
    @return: True to continue processing, False to wait for the next message
    @rtype: boolean
    '''
    while self.alive:
      # wait unless signaled
      self.preempt.wait(Constants.SPIN_DELAY)
      # break if we've finished speaking, do not wait for sounds
      if not self.IsPlaying() and not self.preempt.isSet():
        return True
      # break if preempted by another sound
      elif self.preempt.isSet():
        return False
      # process any waiting stream events
      elif message.SpeechEvents is not None:
        self.HandleStreamEvents(message)
    return False

  def CompleteEvent(self, message, barrier):
    '''
    Handle any stream events left in the queue and arrive at the barrier.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Barrier at which the speaker must arrive when it is done
    @type barrier: L{Worker.Barrier}
    '''
    if message.SpeechEvents is not None:
      self.HandleStreamEvents(message, True)
    super(Speaker, self).CompleteEvent(message, barrier)

  def HandleStreamEvents(self, message, finish=False):
    '''
    Process any events within a speech stream at the times when they occur.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param finish: Process all remaining messages?
    @type finish: boolean
    '''
    # if we have events left to process, see if we've passed any
    while not message.SpeechEvents.IsEmpty() and \
          (finish or \
           self.speech_src.CurrentSample >= message.SpeechEvents.Peek()):
      # grab the event with the lowest sample num
      smsg = message.SpeechEvents.Pop()
      # if it's an internal sound event, play the sound
      if smsg.Sound:
        self.sound_src.Sound = self.sound_fac.Create(smsg)
        self.sound_src.Volume = getattr(Config, self.sound_vol)
        self.sound_src.Play()
      elif message.Listen:
        # route a message directly to the source of the output message
        smsg.RouteTo(message.Source)
        smsg.Prepare(message)
        Input.Manager().AddMessage(smsg)
      if self.observer is not None and not smsg.Sound:
        # notify the speaker observer by cloning the message and routing it
        smsg = smsg.Clone()
        smsg.RouteTo(self.observer)
        Input.Manager().AddMessage(smsg)

  def SilenceAll(self):
    '''Stop all sources from playing immediately.'''
    super(Speaker, self).SilenceAll()
    if self.speech_src.IsPlaying():
      self.speech_src.Stop()

class Ambience(Worker.Worker):
  '''
  A virtual environment that fades looping sounds in and out.

  @ivar max_vol: Maximum volume of ambient audio
  @type max_vol: number
  @ivar fade_sec: Duration of linear volume ramps
  @type fade_sec: number
  @ivar sound_fac: Factory that produces sound audio
  @type sound_fac: L{SoundFactory}
  @ivar sound_src: Plays non-verbal audio
  @type sound_src: pySonic.Source
  @ivar incoming: Latest message received
  @type incoming: L{Messages.OutboundMessage}
  @ivar current_sound: Name of the currently playing sound
  @type current_sound: string or None
  '''
  def __init__(self, max_vol=None, fade_sec=2.0):
    '''
    Initialize the object.

    See instance variables for description of parameters.
    '''
    Worker.Worker.__init__(self)
    if max_vol is not None:
      self.max_vol = max_vol
    else:
      self.max_vol = 'master_volume'
    self.fade_sec = fade_sec
    self.current_sound = None

    # create a sound factory and source
    self.sound_fac = SoundFactory()
    self.sound_src = pySonic.Source()
    self.sound_src.Volume = 0

    # start the thread
    self.start()

  def WaitForEvent(self):
    '''
    Wait for an event to occur.

    @return: Event objects or None if the thread dies
    @rtype: tuple
    '''
    # stop all audio before we wait for a new message
    while self.alive:
      # lock to prevent a preemption
      self.plock.acquire()
      # try to get an object and clear the preempt flag if we do
      if self.preempt.isSet():
        m = self.incoming
        self.preempt.clear()
        self.plock.release()
        return (m,)
      else:
        # no message available
        self.plock.release()
      # wait a bit
      time.sleep(Constants.SPIN_DELAY)
    # the thread is dead
    return None

  def AlreadyPlaying(self, message):
    '''
    Checks if the sound in the given message is already playing.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    '''
    return (message.Sound == self.current_sound and not message.Refresh)

  def HandleEvent(self, message):
    '''
    Handle an event by either fading in a new sound or fading out a playing
    sound.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @return: True to continue processing, False to wait for the next message
    @rtype: boolean
    '''
    # fade in a new sound
    if message is not None:
      self.current_sound = message.Sound
      return self.FadeIn(message)
    # fade out an existing sound
    else:
      self.current_sound = None
      return self.FadeOut()

  def FadeIn(self, message):
    '''
    Fade in a new sound starting at the current volume and ending at the max
    volume.

    @return: True if fade completed without preemption, False if not
    @rtype: boolean
    '''
    # create a sound object and assign it to the source
    s = self.sound_fac.Create(message)
    lv = self.sound_src.Volume
    self.sound_src.Sound = s
    # set the source to looping
    self.sound_src.LoopMode = pySonic.Constants.FSOUND_LOOP_NORMAL
    self.sound_src.Volume = lv
    # play the sound
    self.sound_src.Play()
    # compute the loop delay
    mv = getattr(Config, self.max_vol)
    dv = float(mv - self.sound_src.Volume)
    if dv == 0: return True
    delay = self.fade_sec/dv
    # fade in the sound source up to the maximum volume
    while self.sound_src.Volume < mv:
      self.sound_src.Volume += 1
      time.sleep(delay)
      if self.preempt.isSet(): return False
    return True

  def FadeOut(self):
    '''
    Fade out the currently playing sound and then stop it entirely.

    @return: True if fade completed without preemption, False if not
    @rtype: boolean
    '''
    if self.sound_src.Volume > 0:
      # compute the loop delay
      delay = self.fade_sec/float(self.sound_src.Volume)
      # fade out the sound source to zero
      while self.sound_src.Volume > 0:
        self.sound_src.Volume -= 1
        time.sleep(delay)
        if self.preempt.isSet(): return False
    # stop the source entirely
    self.SilenceAll()
    return True

  def SilenceAll(self):
    '''Stop all sources from playing immediately.'''
    if self.sound_src.IsPlaying():
      self.sound_src.Stop()
      self.sound_src.Volume = 0

  def Stop(self):
    '''Preempt playing audio but don't begin playing anything new.'''
    self.plock.acquire()
    self.incoming = None
    self.preempt.set()
    self.plock.release()

  def Play(self, message):
    '''
    Start playing new audio.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    '''
    self.plock.acquire()
    self.incoming = message
    self.preempt.set()
    self.plock.release()

class Intermittent(Player):
  '''
  A layer in a virtual environment that plays a sound intermittently.

  @ivar init_silence: Initial pause before playing the sound
  @type init_silence: float
  @ivar min_silence: Minimum pause between playing the sound
  @type min_silence: float
  @ivar max_silence: Maximum pause between playing the sound
  @type max_silence: float
  @ivar wait_time: Last computed time to wait before playing the sound again
  @type wait_time: float or None
  @cvar RESOLUTION: Multiplier for float min and max silence that determines the
      resolution of the random wait time computed
  @type RESOLUTION: float
  '''
  RESOLUTION = 100.0

  def __init__(self, sound_vol=None, init_silence=3.0, min_silence=10.0,
               max_silence=20.0, autostart=True):
    '''
    Stores the player settings and starts the thread.

    @param sound_vol: Volume of the sound stream
    @type sound_vol: integer
    @param init_silence: Initial pause before playing the sound
    @type init_silence: float
    @param min_silence: Minimum pause between playing the sound
    @type min_silence: float
    @param max_silence: Maximum pause between playing the sound
    @type max_silence: float
    @param autostart: Should the thread loop be started immediately?
    @type autostart: boolean
    '''
    Player.__init__(self, sound_pos=(0,0,0), sound_vol=sound_vol, looping=False,
                    autostart=False)
    self.init_silence = init_silence
    self.min_silence = min_silence
    self.max_silence = max_silence
    self.wait_time = None

    # start the thread
    if autostart: self.start()

  def HandleEvent(self, message, barrier):
    '''
    Sets the initial wait time to the L{init_silence} value.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Unused barrier
    @type barrier: L{Worker.Barrier}
    '''
    self.wait_time = time.time() + self.init_silence
    return True

  def WaitWhileProcessing(self, message, barrier):
    '''
    Check for preemption or thread death while playing.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Unused barrier
    @type barrier: L{Worker.Barrier}
    @return: True to continue processing, False to wait for the next message
    @rtype: boolean
    '''
    while self.alive:
      # wait unless signaled
      self.preempt.wait(Constants.SPIN_DELAY)
      if not self.IsPlaying():
        if self.wait_time is None:
          # compute a new waiting period
          wait = random.randrange(self.min_silence*self.RESOLUTION,
                                  self.max_silence*self.RESOLUTION)/self.RESOLUTION
          self.wait_time = time.time() + wait
        elif self.wait_time < time.time():
          # start playing the sound using the parent version of HandleEvent
          super(Intermittent, self).HandleEvent(message, barrier)
          # reset wait time so it is recomputed
          self.wait_time = None
      # break if preempted by another sound
      if self.preempt.isSet():
        return True
    return False

  def CompleteEvent(self, message, barrier):
    '''
    Resets the waiting time so the sound doesn't play immediately the next time
    one is queued.

    @param message: Output message from some part of the system
    @type message: L{Messages.OutboundMessage}
    @param barrier: Unused barrier
    @type barrier: L{Worker.Barrier}
    '''
    super(Intermittent, self).CompleteEvent(message, barrier)
    self.wait_time = None

