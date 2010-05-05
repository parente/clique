'''
Defines classes that determine what audio is played when and by which speaker or
speakers.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import threading, Queue, time, weakref
import Worker, Constants, Storage
import Input
from Messages import OutboundPacket, OutboundMessage, PacketMessage
from datetime import datetime, timedelta 

class Group(Worker.Worker):
  '''
  Dispatches messages in a packet to speakers.
  
  @ivar im: Reference to the input manager
  @type im: L{Input.Manager.Manager}
  @ivar om: Weak reference to the output manager
  @type on: weakref.proxy to L{Output.Manager.Manager}
  @ivar old: Preempted packet
  @type old: L{Input.Messages.InboundMessage}
  '''
  def __init__(self, om):
    super(Group, self).__init__()
    self.om = weakref.proxy(om)
    self.im = Input.Manager()
    self.old = None
  
  def run(self):
    '''Override the main thread loop to send packet event notifications.'''   
    while self.alive:
      # wait for an event
      event = self.WaitForEvent()
      # notify if the last event was preempted
      if self.old is not None: self.PreemptEvent(*event)
      if event[0] is None: continue
      # notify that the event is being handled
      self.StartEvent(*event)
      if not self.HandleEvent(*event):
        self.old = event
        continue
      if not self.WaitWhileProcessing(*event):
        self.old = event
        continue
      self.CompleteEvent(*event)
      
  def StartEvent(self, packet, *args):
    '''
    Called before processing a packet.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param args: Additional event arguments
    @type args: list
    '''
    if packet.Listen:
      # route a message stating the packet is starting
      pmsg = PacketMessage(Constants.PACKET_START, packet)
      pmsg.RouteTo(packet.Source)
      self.im.AddMessage(pmsg)    
    
  def CompleteEvent(self, packet, *args):
    '''
    Called after processing has finished.
        
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param args: Additional event arguments
    @type args: list
    '''
    if packet.Listen:
      # route a message stating the packet is done
      pmsg = PacketMessage(Constants.PACKET_DONE, packet)
      pmsg.RouteTo(packet.Source)
      self.im.AddMessage(pmsg)
      
  def PreemptEvent(self, packet, *args):
    '''
    Called when a packet is preempted, before starting the next packet.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param args: Additional event arguments
    @type args: list
    '''
    old_packet = self.old[0]
    if old_packet.Listen:
      # route a message stating the packet is preempted
      pmsg = PacketMessage(Constants.PACKET_PREEMPT, packet, old_packet)
      pmsg.RouteTo(old_packet.Source)
      self.im.AddMessage(pmsg)
    self.old = None

class ActiveGroup(Group):
  '''
  Manages packets sent to the active task speakers. Packets either queue or 
  preempt all other waiting packets.
  
  @ivar speech_fac: Pre-render speech factory
  @type speech_fac: L{Speaker.SpeechFactory}
  @ivar speakers: Speakers index by role
  @type speakers: dictionary
  @ivar incoming: Queue of incoming packets
  @type incoming: L{Output.Storage.PeekQueue}
  '''
  def __init__(self, om, speakers):
    '''
    Initialize an instance.

    See instance variables for description of parameters.
    '''
    super(ActiveGroup, self).__init__(om)
    self.speakers = speakers
    # get a speech factory to pre-render for the first speaker
    k = self.speakers.keys()
    k.sort()
    self.speech_fac = self.speakers[k[0]].CloneSpeechFactory()
    # initialize queue and addition lock
    self.incoming = Storage.PeekQueue()
    # start our thread loop running
    self.start()
    
  def Destroy(self):
    '''Quits the thread loop and destroys the speakers.'''
    super(ActiveGroup, self).Destroy()
    for s in self.speakers.values(): s.Destroy()
      
  def WaitForEvent(self):
    '''
    Waits for an event to occur.
    
    @return: Packet to process and a syncronization barrier
    @rtype: 2-tuple of L{Messages.OutboundPacket} and L{Worker.Barrier}
    '''
    while self.alive:
      try:
        # lock to prevent a preemption
        self.plock.acquire()
        # try to get an object and clear the preempt flag if we do
        p = self.incoming.get(True, Constants.SPIN_DELAY)
        self.preempt.clear()
        self.plock.release()
        # return the packet and a new barrier
        return (p, Worker.Barrier(p.Size))
      except Queue.Empty:
        # no packet available, release the preempt lock
        self.plock.release()
    # the thread is dead
    return (None,)
    
  def HandleEvent(self, packet, barrier):
    '''
    Handles a new packet by sending its messages to their intended speakers.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param barrier: Sychronization object for speakers
    @type barrier: L{Worker.Barrier}    
    '''
    # give instructions to all speakers in the group
    for person in self.speakers:
      try:
        # try to play a message
        m = packet.GetMessage(person)
        self.speakers[person].Play(m, barrier)
      except KeyError, e:
        # stop current audio
        self.speakers[person].Stop()
    return True
    
  def WaitWhileProcessing(self, packet, barrier):
    '''
    Waits until all speakers reach the sync barrier, a packet preempts the 
    current packet, or the thread terminates.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param barrier: Synchronization object for speakers
    @type barrier: L{Worker.Barrier}
    '''
    index = 0
    while self.alive:
      if self.preempt.isSet():
        return False
      # break if all speakers have arrived at the barrier
      elif barrier.IsDone():
        return True
      time.sleep(Constants.SPIN_DELAY)
      # prerender speech waiting for the primary speaker
      try:
        waiting_packet = self.incoming.Peek(index)
        m = waiting_packet.GetMessage(Constants.CONTENT)
        m.Prepare(self.speech_fac)
      except (IndexError, KeyError, Queue.Empty):
        pass
      index += 1
    return False
    
  def Stop(self):
    '''Stop all speakers immediately.'''
    self.plock.acquire()
    p = OutboundPacket(self, True)
    # empty the queue by creating a new one
    self.incoming = Storage.PeekQueue()
    self.incoming.put(p)
    self.preempt.set()
    for s in self.speakers.values(): s.Stop()
    self.plock.release()

  def Play(self, packet):
    '''
    Adds a new output packet to the packet queue. Locks to prevent any other 
    additions while the packet is being added in case of preemption. Locks when
    preempting to avoid the preempt flag from getting incorrectly reset in the 
    thread loop.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    '''
    # lock in case we're pre-empting
    if packet.Preemptive:
      # signal we've preempted and store the packet
      self.plock.acquire()
      # empty the queue by creating a new one
      self.incoming = Storage.PeekQueue()
      self.incoming.put(packet)
      self.preempt.set()       
      self.plock.release()
    else:
      # store the packet for processing later
      self.incoming.put(packet)

class InactiveGroup(Group):
  '''
  Manages packets sent to the related and unrelated task speakers. Waits for the
  user to stop input before generating a non-speech digest of all events that 
  occured since the last report. Answers user queries for spoken description of
  all events in the message history. New events are held up while the history
  is being reported.
  
  @ivar speakers: Speakers index by group name (related or unrelated)
  @type speakers: dictionary
  @ivar incoming: Queue of incoming packets
  @type incoming: Queue.Queue
  @ivar immediate: An incoming packet that should be handled immediately
  @type immediate: L{Messages.OutboundMessage}
  @ivar inaction_delay: Delay between last keyboard input and notification (sec)
  @type inaction_delay: float
  @ivar events
  @type events
  '''  
  def __init__(self, om, speakers, inaction_delay=1.25):
    '''
    Initialize an instance.
    
    See instance variables for description of parameters.
    '''
    super(InactiveGroup, self).__init__(om)
    self.speakers = speakers
    # initialize queue and immediate message holder
    self.incoming = Queue.Queue()
    self.immediate = None
    # initialize dictionary of events to report
    self.events = {}
    # store inaction delay
    self.inaction_delay = inaction_delay
    # start our thread loop
    self.start()
    
  def Destroy(self):
    '''Quit our thread loop and destroy any workers.'''
    super(InactiveGroup, self).Destroy()
    for s in self.speakers.values(): s.Destroy()
    
  def FilterEvents(self):
    '''
    Stores all waiting packets in a dictionary keyed by source ID. Later filter
    operations replace events in the dictionary with newer events from the
    same source.
    '''
    # process all waiting packets
    while 1:
      try:
        # try to get a waiting packet
        packet = self.incoming.get(False)
      except Queue.Empty:
        # quit if there are no more packets
        break
      else:
        # keep only the newest packet from each source
        try:
          self.events[packet.Source.ID] = (packet, packet.Source.ID)
        except ReferenceError:
          pass
        else:
          # make the packet non-preemtive
          packet.Preemptive = False

  def WaitForEvent(self):
    '''
    Waits for a history request from the user or a break in user input.
    
    @return: Packet to process and a syncronization barrier
    @rtype: 2-tuple of L{Messages.OutboundPacket} and L{Worker.Barrier}
    '''
    while self.alive:
      # see if we have a preemptive packet waiting
      if self.preempt.isSet():
        self.plock.acquire()
        # handle a preemptive packet immediately
        packet = self.immediate
        self.preempt.clear()
        self.plock.release()
        return (packet, Worker.Barrier(1))
      
      # filter inactive notifications
      self.FilterEvents()
      
      # notify if user is inactive
      if time.time()-self.im.LastEventTime > self.inaction_delay:
        # take the newest filtered event
        e = self.events.values()
        e.sort()
        try:
          packet, i = e.pop(0)
          del self.events[packet.Source.ID]
        except ReferenceError:
          # the event source died
          del self.events[i]
        except IndexError:
          # there are no events waiting
          time.sleep(Constants.SPIN_DELAY)
          continue
        # add it to the history
        self.om.PutHistory(packet)
        # play it
        return (packet, Worker.Barrier(1))
        
      # sleep for a bit
      time.sleep(Constants.SPIN_DELAY)

    # the thread is dead
    return (None,)
    
  def HandleEvent(self, packet, barrier):
    '''
    Handles a new packet by sending its messages to their intended speakers.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param barrier: Sychronization object for speakers
    @type barrier: L{Worker.Barrier}
    @return: Always true to wait while processing
    @rtype: boolean
    '''
    # stop all players
    self.SilenceAll()
    if packet.Preemptive:
      # if all is quiet, speak and play the sound
      m = self.FindMostInformative(packet)
      if m is None: return False
      self.speakers[packet.Group].Play(m, barrier)
    else:
      if True: #self.om.IsSilent():
        # @note: always speaking now, even when busy
        # if all is quiet, speak and play the sound
        m = self.FindMostInformative(packet)
        self.speakers[packet.Group].Play(m, barrier)
      else:
        # otherwise, play just a sound
        m = self.FindFirstSound(packet)
        try: 
          m = m.CloneSoundOnly()
        except AttributeError:
          return False
        self.speakers[packet.Group].Play(m, barrier)
    return True
    
  def WaitWhileProcessing(self, packet, barrier):
    '''
    Wait until all speakers reach the sync barrier, a packet preempts the 
    current packet, or the thread terminates.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param barrier: Sychronization object for speakers
    @type barrier: L{Worker.Barrier}
    '''
    while self.alive:
      if self.preempt.isSet():
        return False
      # break if all speakers have arrived at the barrier
      elif barrier.IsDone():
        return True
      time.sleep(Constants.SPIN_DELAY)
    return False
    
  def FindMostInformative(self, packet):
    '''
    Search a packet for the message that has the most text. Failing that, find 
    the lowest numbered message that has a sound.
    
    @param packet: Output packet with messages to search
    @type packet: L{Messages.OutboundPacket}
    @return: Message that meets the desired criteria or None if not found
    @rtype: L{Messages.OutboundMessage} or None    
    '''
    curr = (None, '', None)
    for m in packet:
      if m.Speech is not None and len(m.Speech) > len(curr[1]):
        curr = (m, m.Speech, m.Sound)
      # NOTE: changed from curr[2], seemed wrong
      elif curr[0] is None and m.Sound is not None:
        curr = (m, m.Speech, m.Sound)
    return curr[0]
    
  def FindFirstSound(self, packet):
    '''
    Searches a packet for the lowest numbered message that has a sound.
    
    @param packet: Output packet with messages to search
    @type packet: L{Messages.OutboundPacket}
    @return: Message that meets the desired criteria or None if not found
    @rtype: L{Messages.OutboundMessage} or None
    '''
    # don't look at looping sounds
    if packet.IntendedGroup == Constants.CONTEXT:
      try:
        return packet.GetMessage(Constants.CHANGE)
      except KeyError:
        return None
    # look at the first sound in other groups
    for m in packet:
      if m.Sound is not None:
        return m
    return None
    
  def SilenceAll(self):
    '''Stop all speakers immediately.'''
    for s in self.speakers.values(): s.Stop()

  def Stop(self):
    self.plock.acquire()
    self.immediate = OutboundPacket(self, True)
    self.preempt.set()
    self.SilenceAll()  
    self.plock.release()
    
  def Play(self, packet):
    '''
    Adds a new packet to the packet queue or preempts playing audio with a 
    preemptive packet.
    
    @param packet: Packet containing output messages
    @type packet: L{Messages.OutboundPacket}
    '''
    # lock in case we're preempting
    if packet.Preemptive:
      # this is a response to a user request
      self.plock.acquire()
      self.immediate = packet
      self.preempt.set()
      self.plock.release()
    else:
      # this is a response to some async system event
      self.incoming.put(packet)
   
class ContextGroup(Group):
  '''
  Manages packets sent to the context players. Context change indicators queue
  or play immediately. Loops or intermittent sounds representing program and 
  task context play immediately always. Program context loops fade in and out.
  
  @ivar players: Dictionary of players either ambient, looping, or standard
  @type players: dictionary
  @ivar curr: Index of the active ambient worker in the worker pool
  @type curr: number  
  '''
  def __init__(self, om, players):
    '''
    Initialize an instance.
    
    See instance variables for a description of parameters.
    '''
    super(ContextGroup, self).__init__(om)
    self.players = players
    self.curr = 0
    self.incoming = Queue.Queue()
    
    # start our thread loop
    self.start()
    
  def Destroy(self):
    '''Quit our thread loop and destroy any workers.'''
    super(ContextGroup, self).Destroy()
    for p in self.players.values(): 
      try:
        p.Destroy()
      except AttributeError:
        for a in p: a.Destroy()
    
  def WaitForEvent(self):
    '''
    Wait for an event to occur.
    
    @return: Collection of output messages
    @rtype: 1-tuple of L{Messages.OutboundPacket}
    '''
    while self.alive:
      try:
        # lock to prevent a preemption
        self.plock.acquire()
        # try to get an object and clear the preempt flag if we do
        p = self.incoming.get(True, Constants.SPIN_DELAY)
        self.preempt.clear()
        self.plock.release()
        # return the packet and a new barrier
        return (p, Worker.Barrier(1))
      except Queue.Empty:
        # no packet available, release the preempt lock
        self.plock.release()
    # the thread is dead
    return (None,)
    
  def HandleEvent(self, packet, barrier):
    '''
    Handles a new event by playing or queueing the context change message,
    playing the task loop, and playing the ambience if each exists.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param barrier: Synchronization object for speakers
    @type barrier: L{Worker.Barrier}    
    @return: True if waiting for a task change sound, False if not
    @rtype: boolean
    '''
    # give the context change player its message
    try:
      msg = packet.GetMessage(Constants.CHANGE)
      if packet.Preemptive:
        self.players[Constants.CHANGE].Play(msg, barrier)
      else:
        self.players[Constants.CHANGE].PlayLater(msg, barrier)
      cont = True
    except KeyError:
      cont = False
    # give the task context loop player its message and a null barrier
    try:
      msg = packet.GetMessage(Constants.LOOPING)
      self.players[Constants.LOOPING].Play(msg, Worker.Barrier(1))
    except KeyError:
      self.players[Constants.LOOPING].Stop()
    # give the intermittent player its message and a null barrier
    try:
      msg = packet.GetMessage(Constants.INTERMITTENT)
      self.players[Constants.INTERMITTENT].Play(msg, Worker.Barrier(1))
    except KeyError:
      self.players[Constants.INTERMITTENT].Stop()
    # give the ambience player the new ambience if requested
    try:
      msg = packet.GetMessage(Constants.AMBIENCE)
    except KeyError:
      pass
    else:
      p = self.players[Constants.AMBIENCE][self.curr]
      if not p.AlreadyPlaying(msg):
        # stop the current ambience only if it is different than the one we want
        # to start playing now
        p.Stop()
        # start the new ambience
        self.curr = (self.curr + 1) % len(self.players[Constants.AMBIENCE])
        np = self.players[Constants.AMBIENCE][self.curr]
        # make sure it's stopped
        np.SilenceAll()
        np.Play(msg)
    return cont
    
  def WaitWhileProcessing(self, packet, barrier):
    '''
    Waits until the context change player reaches the sync barrier, a packet 
    preempts the current packet, or the thread terminates.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    @param barrier: Synchronization object for speakers
    @type barrier: L{Worker.Barrier}       
    '''
    while self.alive:
      if self.preempt.isSet():
        return False
      # break if all speakers have arrived at the barrier
      elif barrier.IsDone():
        return True
      time.sleep(Constants.SPIN_DELAY)
    return False    
    
  def Play(self, packet):
    '''
    Adds a new packet to the queue and preempts playing audio.
    
    @param packet: Collection of output messages
    @type packet: L{Messages.OutboundPacket}
    '''
    self.plock.acquire()
    self.incoming.put(packet)
    self.preempt.set()
    self.plock.release()
    
if __name__ == '__main__':
  pass
