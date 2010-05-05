'''
Defines the structure of outbound and feedback messages.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import aspell, re, weakref, time
import Input, Interface
import Constants

# global objects used for spell checking
ltgt_regex = re.compile('(<)|(>)')
spell_checker = aspell.spell_checker(prefix='c:/program files/aspell') 

class SpellXlator(dict):
  '''
  Prepares normal text to be spelled by the speech engine. Replaces punctuation with
  their names. Spaces out other characters. Implements the Singleton pattern by 
  overriding the class definition with an instance of the same name.
  
  This class is based on the Xlator class by Xavier Defrang.
  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/81330/
  
  @ivar punc_map: Mapping from character to that character's name
  @type punc_map: dictionary
  @ivar regex: Regular expression used to replace punctuation
  @type regex: re object
  '''
  def __init__(self, punc_map):
    '''
    Initializes an instance.
    
    See instance variables for parameter description.
    '''
    self.punc_map = punc_map
    self.regex = self.makeRegex()
  
  def makeRegex(self):
    '''Compiles the regular expression.'''
    return re.compile('.')
  
  def __call__(self, match):
    '''
    Builds a pronunciation correction for the provided match object.
      
    @param match: Word identified to have its pronunciation fixed
    @type match: re.MatchObject
    '''
    c = match.group(0)
    try:
      return '%s,' % self.punc_map[c]
    except:
      if ord(c) < 128:
        return '<spell>%s</spell>' % c
      else:
        return 'blank'

  def Translate(self, text):
    '''
    Replace words in a text segment with pronunciation corrections.
    
    @param text: Segment of text with words needing correction
    @type text: string
    '''
    if text is not None:
      return self.regex.sub(self, text)
    else:
      return None
SpellXlator = SpellXlator(Constants.CHARACTER_MAP)

class OutboundPacket(object):
  '''
  Request for output from some part of the system directed to some group. Holds 
  individual messages directed to particular speakers. Acts as a synchronizer for 
  speech events directed at multiple speakers in a single group.
  
  @ivar Source: Object that initiated the output
  @type Source: weakref.proxy for L{Output.Manager.Pipe}
  @ivar Group: Group to which this message is directed now
  @type Group: integer
  @ivar IntendedGroup: Group to which this message was originally directed
  @type IntendedGroup: integer
  @ivar InputMessage: Input message that triggered this output event
  @type InputMessage: L{Input.Messages.InboundMessage} or None
  @ivar Listen: Is the source listening for packet events?
  @type Listen: boolean
  @ivar Name: Optional identifying name for this packet
  @type Name: string  
  @ivar Preemptive: Does this packet preempt others?
  @type Preemtpive: boolean
  @ivar messages: Individual output messages to be handled by speakers
  @type messages: dictionary of L{OutboundMessage}
  '''
  def __init__(self, source, message, group=Constants.ACTIVE_CTRL, 
               listen=False, name=None):
    '''
    Initialize the object.
    
    @param Source: Object that initiated the output
    @type Source: weakref.proxy for L{Output.Manager.Pipe}
    @param message: Input message that triggered this output event
    @type message: L{Input.Messages.InboundMessage} or None
    @param group: Group to which this message is directed
    @type group: number
    @param listen: Is the source listening for packet events?
    @type listen: boolean
    @param name: Optional identifying name for this packet
    @type name: string
    '''
    self.Initialize(source, message, group, listen, name)
    self.Time = 0
    self.messages = {}
    
  def __iter__(self):
    '''
    @return: Ascending key-order iterator over stored messages
    @rtype: list iterator
    '''
    order = self.messages.keys()
    order.sort()
    return iter([self.messages[k] for k in order])
    
  def __cmp__(self, other):
    '''
    Compares this packet to another for sorting by time.
    
    @return: 1 if this packet is newer, 0 if the same age, or -1 if older
    @rtype: integer
    '''
    if self.Time < other.Time:
      return -1
    elif self.Time > other.Time:
      return 1
    else:
      return 0
      
  def Initialize(self, source, message, group, listen, name):
    '''
    Initializes some packet properties. Accepts the same parameters as the
    constructor so it can be used to re-initialize a packet a later time.
    
    See constructor for parameter descriptions.
    '''
    try:
      self.Source = weakref.proxy(source)
    except TypeError:
      # probably weak already or None, hold a strong reference
      self.Source = source
    self.Group = group
    self.IntendedGroup = group
    self.InputMessage = message
    self.Listen = listen
    self.Name = name
    self.Preemptive = self.InputMessage is not None
    
  def GetMessage(self, i):
    '''
    Gets a message in a packet.
    
    @param i: Person retrieving the messages
    @type i: number
    @return: Message directed to person i
    @rtype: L{Messages.OutboundMessage}
    @raise IndexError: Person does not exist
    '''
    return self.messages[i]
    
  def UpdateMessage(self, person, **kwargs):
    '''
    Modifies a message in a packet.
    
    @param kwargs: New named values for the packet
    @type kwargs: dictionary
    '''
    m = self.messages[person]
    m.Update(**kwargs)
    
  def AddMessage(self, person=0, speech=None, sound=None, spell=False, 
                 letters=False, listen=False, bookmarks=None, name=None,
                 refresh=False, **kwargs):
    '''
    Adds a new message to the packet.
    
    @param person: Person to which this message is directed
    @type person: number
    @param speech: Text to speak
    @type speech: string
    @param sound: Sound filename to play
    @type sound: string
    @param spell: Should any speech be spell checked?
    @type spell: boolean
    @param letters: Should the text be spelled out letter by letter?
    @type letters: boolean
    @param listen: Is an object listening for speech stream events?
    @type listen: boolean
    @param bookmarks: Bookmarks to be embedded in the speech stream
    @type bookmarks: list of L{BookmarkMessage}
    @param name: Arbitrary user data string
    @type name: string
    @param refresh: Forces a refresh of the output source
    @type refresh: boolean
    @param kwargs: Other arguments, currently unused
    @type kwargs: dictionary
    '''
    m = OutboundMessage(self.Source, speech, sound, spell, letters, 
                        listen, bookmarks, name, refresh)
    self.messages[person] = m
    
  def GetSize(self):
    '''
    @return: Number of messages in the packet
    @rtype: number
    '''
    return len(self.messages)
  Size = property(GetSize)
  
  def Unprepare(self):
    '''
    Unprepares all messages. Useful when packet will be stored for a long time
    and should not take up a ton of memory.
    '''
    for m in self.messages.values():
      m.Unprepare()
    
  def RouteTo(self, group):
    '''
    Specifies to which group the packet should be routed.
    
    @param group: Group to which the packet should be sent
    @type group: number
    '''
    self.Group = group
    # make messages from outside the focus un-preemptive
    if group >= Constants.ACTIVE_PROG:
      self.Preemptive = False
    
  def StampTime(self):
    '''
    Stores the time at which this message was received for processing. Only
    allows one stamp.
    '''
    if not self.Time:
      self.Time = time.time()

class OutboundMessage(object):
  '''
  Request for output from some part of the system. Holds information about 
  speech and non-speech sounds.
  
  @ivar Source: Object that initiated the output
  @type Source: weakref.proxy for L{Output.Manager.Pipe}
  @ivar Speech: Text to speak
  @type Speech: string
  @ivar Sound: Name of a sound file to play
  @type Sound: string
  @ivar Spell: Should the text be spell checked?
  @type Spell: boolean
  @ivar Letters: Should the text be spelled out letter by letter?
  @type Letters: boolean
  @ivar Punctuation: Should punctuation be pronounced?
  @type Punctuation: boolean
  @ivar Listen: Is the source interested in speech events?
  @type Listen: boolean
  @ivar Bookmarks: Bookmark messages placed in the speech stream
  @type Bookmarks: list of L{BookmarkMessage}
  @ivar IsXML: Does the speech contain XML commands?
  @type IsXML: boolean
  @ivar SpeechAudio: Rendered speech
  @type SpeechAudio: pySonic.Sound
  @ivar SpeechEvents: Speech stream events
  @type SpeechEvents: L{Output.StreamEvents.Queue}
  @ivar Name: Optional identifying name for this message
  @type Name: string
  @ivar Refresh: Forces a refresh of the output source
  @type Refresh: boolean
  '''
  def __init__(self, source, speech=None, sound=None, spell=False, 
               letters=False, listen=False, bookmarks=None, name=None,
               refresh=False):
    '''
    Initialize the object.
    
    @param source: Object from which the output message originated
    @type source: weakref.proxy for L{Output.Manager.Pipe}
    @param speech: Text to speak
    @type speech: string
    @param sound: Name of a sound file to play
    @type sound: string
    @param spell: Should the text be spell checked?
    @type spell: boolean
    @param letters: Should the text be spelled out letter by letter?
    @type letters: boolean
    @param listen: Is the source interested in speech events?
    @type listen: boolean
    @param bookmarks: Bookmark messages to be placed in the speech stream
    @type bookmarks: list of L{BookmarkMessage}
    @param name: Optional identifying name for this message
    @type name: string
    @param refresh: Forces a refresh of the output source
    @type refresh: boolean
    '''
    # hold onto the passed parameters
    self.Source = source
    self.Speech = speech
    self.Sound = sound
    self.Spell = spell
    self.Letters = letters
    self.Listen = listen
    self.Bookmarks = bookmarks or []
    self.IsXML = False
    self.SpeechAudio = None
    self.SpeechEvents = None
    self.Name = name
    self.Refresh = refresh
    
  def Clone(self):
    '''
    Makes an exact clone of this message.
    
    @return: Clone of this message
    @rtype: OutboundMessage
    '''
    o = OutboundMessage(self.Source, self.Speech, self.Sound, self.Spell, 
                        self.Letters, self.Listen, self.Bookmarks, self.Name,
                        self.Refresh)
    o.IsXML = self.IsXML
    return o
    
  def CloneSoundOnly(self):
    '''
    Makes a clone of this message minus any speech.
    
    @return: Clone of this message without speech
    @rtype: OutboundMessage
    '''
    o = OutboundMessage(self.Source, None, self.Sound, False, False, 
                        self.Listen, None, None, self.Refresh)
    return o
    
  def Update(self, **kwargs):
    '''
    Updates all fields named in keyword arguments. This will not unprepare or
    re-prepare a message so updates will not have the desired effect after
    the message has been prepared.
    
    @param kwargs: Named fields to update
    @type kwargs: dictionary
    '''
    for key, val in kwargs.items():
      name = key.title()
      setattr(self, name, val)
    
  def Prepare(self, speech_fac):
    '''
    Called to prepare the speech data for output. Might be executed even if the
    message is never output in a lookahead render op.
    '''
    # check if speech needs to be processed
    if self.Speech is not None:
      # make sure we have a real string now
      self.Speech = str(self.Speech)
      # pronounce single punctuation
      if len(self.Speech) == 1:
        self.ProcessSingleCharacter()
      # or spell text character by character
      elif self.Letters:
        self.ProcessLetters()
      # or spell check words
      elif self.Spell:
        self.SpellCheck()
      # process any bookmarks if not spelling by latters and marks exist
      if not self.Letters and len(self.Bookmarks) > 0:      
        self.ProcessBookmarks()
    
    # render speech the first time prepared only
    if self.SpeechAudio is None:
      # render speech using the provided speech factory
      self.SpeechAudio, self.SpeechEvents = speech_fac.Create(self)

    # return the audio data as the result
    return self.SpeechAudio
    
  def Unprepare(self):
    '''Throws away pre-rendered speech to unprepare for long term storage.'''
    self.SpeechAudio = None
    self.SpeechEvents = None
    
  def EscapeXML(self):
    '''Escapes XML characters already in the text before adding commands.'''
    if not self.IsXML:
      # the speech will contain XML
      self.IsXML = True
      # escape all < and >
      self.Speech = re.sub('<', '&lt', self.Speech)
      self.Speech = re.sub('>', '&gt', self.Speech)
    
  def SpellCheck(self):
    '''Create mispelling bookmarks.'''
    p = 0
    words = self.Speech.split(' ')
    for i in range(len(words)):
      # make sure it's not a number
      try:
        float(words[i])
        continue
      except ValueError:
        pass
      if not spell_checker.check(words[i].strip(Constants.SPELL_FILTER)):
        self.Bookmarks.append(BookmarkMessage(p, 
                              Interface.ISound(self).State('misspelled')))
      p += len(words[i])+1
      
  def ProcessSingleCharacter(self):
    '''Wraps a single character in spell tags so it is spoken properly.'''
    self.IsXML = True
    self.Speech = SpellXlator.Translate(self.Speech)
      
  def ProcessLetters(self):
    '''Wraps text in spell tags so words are read letter by letter.'''
    self.EscapeXML()
    # replace all punctuation characters with their names
    self.Speech = SpellXlator.Translate(self.Speech)
    
  def ProcessBookmarks(self):
    '''Insert XML bookmarks in the speech stream.'''
    # find where all < and > signs are in the string
    # positions are needed because our bookmark locations change when we escape
    pos = [m.start() for m in ltgt_regex.finditer(self.Speech)]
    # escape the XML
    self.EscapeXML()
    # sort the bookmarks
    self.Bookmarks.sort()
    # run through all the bookmark objects and add them to the text as XML
    tag_offset = 0
    bm_offset = 0
    for b in self.Bookmarks:
      # keep track of any offsets caused by escaping        
      while len(pos) > 0 and b.Position > pos[0]:
        pos.pop(0)
        tag_offset += 2
      # insert the bookmark XML at the proper position
      self.Speech = self.Speech[:b.Position+tag_offset+bm_offset] + \
                    str(b) + \
                    self.Speech[b.Position+tag_offset+bm_offset:]
      # update the bookmark position and track the XML offset
      b.Position += tag_offset
      bm_offset += b.Length

class BookmarkMessage(object):
  '''
  Describes metadata inserted into a speech stream that will trigger events
  when encountered.
  
  @ivar Kind: Type of bookmark, currently BM_SOUND or BM_SPEECH
  @type Kind: number
  @ivar Position: Character offset into the speech text
  @type Position: number
  @ivar Payload: Data attached to the bookmark
  @type Payload: string
  @ivar bookmark_string: XML representation of the bookmark
  @type bookmark_string: string
  @ivar Length: Size of the bookmark string in characters
  @type Length: number
  '''
  def __init__(self, position, payload, kind=Constants.BM_SOUND):
    '''
    Initialize the object.
    
    See instance variable for description of parameters.
    '''
    self.Kind = kind
    self.Position = position
    self.Payload = payload
    
    # compute the bookmark length and its string
    self.bookmark_string = '<bookmark mark="%d:%s" />' % (self.Kind, self.Payload)
    self.Length = len(self.bookmark_string)
    
  def __cmp__(self, o):
    '''
    Allow bookmarks to sort based on position.
    
    @param o: Bookmark to compare this one against
    @type o: BookmarkMessage
    @return: -1,0,1 if self before, at, or after o
    @rtype: number
    '''
    if self.Position == o.Position: return 0
    elif self.Position < o.Position: return -1
    else: return 1
    
  def __repr__(self):
    '''
    @return: XML representation of the bookmark
    @rtype: string
    '''
    return self.bookmark_string
    
class PacketMessage(Input.InboundMessage):
  '''
  Notification of an event during packet processing.
  
  @ivar Packet: Packet doing the preemption
  @type Packet: L{OutboundPacket}
  @ivar Old: Preempted packet
  @type Old: L{OutboundPacket}
  '''
  def __init__(self, ID=None, packet=None, old=None):
    '''
    Initialize an instance.
    
    See instance variables for parameter descriptions.
    '''
    super(PacketMessage, self).__init__(ID)
    self.Packet = packet
    self.Old = old

class StreamMessage(Input.InboundMessage):
  '''
  Notification of an event within a speech stream. 
  
  @ivar ID: Internal message tuple
  @type ID: 2-tuple of number  
  @ivar Sound: Name of a sound that should play in response to this event
  @type Sound: string
  @ivar Text: Text spoken that caused this event
  @type Text: string
  @ivar AllText: Text that produced the speech stream, including XML markup
  @type Text: string
  @ivar RawPosition: Character at which the event occurred, counting XML markup
  @type RawPosition: number
  @ivar TruePosition: Character at which the event occurred, leaving out XML markup
  @type TruePosition: number  
  @ivar Difference: Number of characters between the point at which this event occurred
                    and the point at which the last event occurred
  @type Difference: number
  @ivar Name: Optional identifying name for this message
  @type Name: string
  '''
  def __init__(self, sound=None, ID=None, text=None, raw_position=None,
               true_position=None, difference=None, all_text=None,
               name=None):
    '''
    Initializes the object by storing all params as instance variables.
    
    See instance variables for description of parameters.
    '''
    # hold onto passed parameters
    super(StreamMessage, self).__init__(ID)
    self.Sound = sound
    self.Text = text
    self.AllText = all_text
    self.RawPosition = raw_position
    self.TruePosition = true_position
    self.Difference = difference
    self.Name = None
    
  def Clone(self):
    '''
    Makes a deep copy of this object so that the original can be routed to one
    source and the clone to another.
    
    @return: Deep copy of this object sharing no references with the original
    @rtype: L{StreamMessage}
    '''
    return StreamMessage(sound=self.Sound, ID=self.ID, text=self.Text, 
                         raw_position=self.RawPosition, 
                         true_position=self.TruePosition, 
                         difference=self.Difference, all_text=self.AllText,
                         name=self.Name)

  def Prepare(self, message):
    '''
    Updates this stream message with information from the outbound message that
    triggered it.
   
    @param message: Original message
    @type message: L{OutboundMessage}
    '''
    self.Name = message.Name
    
if __name__ == '__main__':
  p = OutboundPacket(object, object)
  p.AddMessage(person=0, speech='<Thiss> is a testt of the <systeem >. Oncee upon a time, there was a < little boyy.', spell=True)
  p.AddMessage(person=1, speech='http://www.cs.unc.edu', letters=True)
  m = p.GetMessage(0)
  m.Prepare()
  m = p.GetMessage(1)
  m.Prepare()
