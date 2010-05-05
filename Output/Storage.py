'''
Defines queue and ring data structures for storing output events.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import pyTTS, re, Queue, time
import Constants, Config
from protocols import advise
from Messages import StreamMessage
from Interface import IOption, IDeletable
from Chooser import Chooser

class PeekQueue(Queue.Queue):
  '''Thread-safe queue of items that allows lookahead without removal.'''
  def Peek(self, index):
    '''
    Return an item at the given index. Do not remove the item from the queue.

    @param index: Index of the item to retrieve
    @type index: integer
    @raise: IndexError, Queue.Empty
    '''
    self.not_empty.acquire()
    try:
      if self._empty():
        raise Queue.Empty
      item = self.queue[index]
      return item
    finally:
      self.not_empty.release()

class StreamQueue(object):
  '''
  Queue of events within a speech stream sorted by order of occurence.

  @ivar events: Events of interest
  @type events: list of pyTTS.Event
  @ivar text: All text in the stream
  @type text: string
  @ivar offset: Offset of the true position to correct for XML tags
  @type offset: number
  @ivar last_pos: Last character position at which an event occurred
  @type last_pos: number
  @ivar tags: Location of XML tags in the text; used to compute offset
  @type tags: list of L{Messages.BookmarkMessage}
  '''
  def __init__(self, tts_events, message, divisor=1):
    '''
    Initialize the object.

    @param tts_events: All stream events
    @type tts_events: list of pyTTS.Event
    @param message: Metadata about this output stream
    @type message: L{Messages.OutboundMessage}
    @param divisor: Divisor to convert from event byte position to sample number
    @type divisor: number
    '''
    f = [pyTTS.tts_event_word, pyTTS.tts_event_bookmark,
         pyTTS.tts_event_end_stream]
    # store the events of interest
    self.events = filter(lambda e: e.EventType in f, tts_events)
    # fix stream offsets based on the bits per sample
    for e in self.events: e.StreamPosition /= divisor

    # compute offsets caused by xml tags and encoded characters in the stream
    self.text = message.Speech
    # duplicate so when we pop bookmarks we don't destroy the original list
    self.tags = [b for b in message.Bookmarks]
    self.offset = 0
    self.last_pos = 0

  def IsEmpty(self):
    '''
    @return: Is the queue empty?
    @rtype: boolean
    '''
    return len(self.events) == 0

  def Peek(self):
    '''
    Get the sample number at which the earliest event in the queue occurs.

    @return: Sample number
    @rtype: number
    '''
    return self.events[0].StreamPosition

  def Pop(self):
    '''
    Retrieve the earliest event in the queue by removing it from the queue.

    @return: Stream event message
    @rtype: L{Messages.StreamMessage}
    '''
    # get the top event
    e = self.events.pop(0)
    if e.EventType == pyTTS.tts_event_bookmark:
      cmd, payload = e.Name.split(':')
      if int(cmd) == Constants.BM_SOUND:
        return StreamMessage(sound=payload)
    elif e.EventType == pyTTS.tts_event_word:
      # offset the position by any xml tags in the stream
      while len(self.tags) > 0 and \
            e.CharacterPosition+self.offset > self.tags[0].Position:
        b = self.tags.pop(0)
        self.offset -= b.Length
      # compute the difference between the current and last position
      tp = e.CharacterPosition+self.offset
      diff = tp - self.last_pos
      self.last_pos = tp
      return StreamMessage(ID=Constants.SAY_WORD,
               text=self.text[e.CharacterPosition:e.CharacterPosition+e.Length],
               raw_position=e.CharacterPosition, true_position=tp,
               difference=diff, all_text=self.text)
    elif e.EventType == pyTTS.tts_event_end_stream:
      # offset the position by any xml tags in the stream
      while len(self.tags) > 0:
        b = self.tags.pop(0)
        self.offset -= b.Length
      # compute the difference between the current and last position
      tp = len(self.text)+self.offset
      diff = tp - self.last_pos
      self.last_pos = tp
      return StreamMessage(ID=Constants.SAY_DONE, raw_position=len(self.text),
                           true_position=tp, difference=diff)

class HistoryRing(object):
  '''
  Ring buffer for storing a history of past output packets.

  @ivar max_size: Maximum allowed size of the queue
  @type max_size: number
  @ivar queue: List of stored items
  @type queue: list
  @ivar curr: Current index into the queue
  @type curr: number
  '''
  def __init__(self, max_size=10):
    '''
    Initialize an instance.

    See instance variables for parameter descriptions.
    '''
    self.max_size = max_size
    self.queue = []
    self.curr = 0

  def __iter__(self):
    return iter(self.queue)

  def GetSize(self):
    '''
    @return: Current size of the queue
    @rtype: number
    '''
    return len(self.queue)
  Size = property(GetSize)

  def Push(self, item):
    '''
    Add a new element to the queue while maintaining the max size invariant.

    @param item: Item to store
    @type item: object
    '''
    # pop oldest element to maintain size invariant
    if self.Size >= self.max_size:
      self.queue.pop()
    self.queue.insert(0, item)
    self.curr = 0

  def IsEmpty(self):
    '''
    @return: Is the queue empty?
    @rtype: boolean
    '''
    return len(self.queue) == 0

class MemoryChunk(object):
  '''
  Chunk of text stored in long term memory in the L{MemoryBuffer}.

  Provides L{IOption} interface for use by a L{Chooser}.

  @ivar create_time: Time when this chunk was created
  @type create_time: float
  @ivar subject: Piece of text to be stored in memory
  @type subject: string
  '''
  advise(instancesProvide=[IOption])

  def __init__(self, subject):
    '''
    Stores the subject and notes the creation time of this chunk.

    @param subject: Piece of text to be stored in memory
    @type subject: string
    '''
    self.subject = subject
    self.create_time = time.time()

  def __str__(self):
    return self.subject

  def GetTime(self):
    '''
    @return: Time when this chunk was created
    @rtype: float
    '''
    return self.create_time

  def GetName(self):
    '''
    @return: Text chunk
    @rtype: string
    '''
    return self.subject

  def GetObject(self):
    '''
    @return: Text chunk
    @rtype: string
    '''
    return self.subject

class MemoryBuffer(Chooser):
  '''
  Buffer for long term remembrance of chunks of text.

  @ivar active: Is someone browsing the memory?
  @type active: boolean
  @ivar size_threshold: Size of the memory beyond which chunks are considered
      for cleanup
  @type size_threshold: integer
  @ivar time_limit: Maximum lifetime of chunks in minutes. Only takes effect
      when there are more than L{size_threshold} chunks in memory
  @type time_limit: integer
  @ivar working_memory: Temporary buffer for text fragments that will later be
      added to long term memory
  @type working_memory: list
  '''
  advise(instancesProvide=[IDeletable])

  def __init__(self, size_threshold=100, time_limit=60):
    '''
    Stores the size threshold and time limit. Initializes the long and short
    term memory buffers.

    @ivar size_threshold: Size of the memory beyond which chunks are considered
        for cleanup
    @type size_threshold: integer
    @ivar time_limit: Maximum lifetime of chunks in minutes. Only takes effect
        when there are more than L{size_threshold} chunks in memory
    @type time_limit: integer
    '''
    super(MemoryBuffer, self).__init__([])
    self.size_threshold = size_threshold
    self.time_limit = time_limit
    self.working_memory = []
    self.active = False
    self.indices = [-1, -1]

  def __iter__(self):
    '''Iterates over all items in the working buffer.'''
    chunks = list(self.options)
    chunks.reverse()
    for mc in chunks:
      yield str(mc)

  def Activate(self):
    '''
    Activates long term memory as a model for L{IEditableList} browsing. Sets
    the pointer to the first, most recent, memory chunk. Sets a flag indicating
    browsing is happening so insertions affect the pointer properly.

    @return: Ready for interaction?
    @rtype: boolean
    '''
    self.Cleanup()
    self.curr = 0
    self.active = True
    return super(MemoryBuffer, self).Activate()

  def Deactivate(self):
    '''
    Deactivates long term memory as a model for L{IEditableList} browsing.
    Unsets a flag indicating browsing is not happening.
    '''
    self.Cleanup()
    self.active = False
    return super(MemoryBuffer, self).Deactivate()

  def Delete(self):
    '''
    Deletes the current chunk from long term memory.
    '''
    try:
      del self.options[self.curr]
    except IndexError:
      return
    if self.curr >= self.GetItemCount():
      self.curr = self.GetItemCount() - 1

  def AddToWorking(self, fragment):
    '''
    Adds a fragment to working memory.

    @param fragment: Start and end index plus text fragment string
    @type fragment: (integer, integer, string)
    '''
    self.working_memory.append(fragment)

  def AddToLongTerm(self):
    '''
    Adds the current contents of working memory to long term memory. Resets the
    working memory buffer.
    '''
    if len(self.working_memory) == 0:
      #Config.log('-1 -1')
      return
    # get the start and end index of the entire run
    #start, end = -1, -1
    #for frag in self.working_memory:
      #if start == -1 and frag[0] >= 0:
        #start = frag[0]
      #if end < frag[1]:
        #end = frag[1]
    #Config.log('%d %d' % (start or -1, end or -1))
    # join all of the text
    self.options.insert(0, MemoryChunk(' '.join(
      (text for a, b, text in self.working_memory))))
    self.working_memory = []
    if self.active:
      self.curr += 1

  def Cleanup(self):
    '''
    Removes old (time-wise) chunks when memory has reached a certain threshold
    size. This strategy allows memory to have a limitless size if the user needs
    to store a tremendous number of items, but also relieves the user from
    some cleanup duties if old items are leftover for long periods of time.
    This method is only called during activation and deactivation so chunks
    never disappear while the user is browsing the contents of memory.

    @todo: is this a good strategy? what about old important items that are
    reused frequently?
    '''
    if self.GetItemCount() > self.size_threshold:
      i = 0
      while i < self.GetItemCount():
        chunk = self.options[i]
        if (chunk.GetTime() + self.time_limit*60) < time.time():
          del self.options[i]
        else:
          i += 1
