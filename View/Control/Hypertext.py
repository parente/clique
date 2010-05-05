'''
Defines classes for handling rich text interaction patterns, namely document
reading.

@todo add link merging opt to avoid interrupting read all flow

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from Interface import IEditableText, IText, IDetailable, ISeekable
import Text
import Base
import Output
import Support
import Config
import re

HEADING_MAP = {'h1' : 'level 1',
            'h2' : 'level 2',
            'h3' : 'level 3',
            'h4' : 'level 4',
            'h5' : 'level 5',
            'h6' : 'level 6'}

SEEK_MAP = {'h' : lambda role, state: role.startswith('h'),
            'l' : lambda role, state: role == 'link',
            'v' : lambda role, state: role == 'link' and 'traversed' in state,
            'u': lambda role, state: role == 'link' and 'traversed' not in state,
            'i': lambda role, state: role == 'list item'
            }

class DocumentReading(Text.TextReading):
  '''
  Navigable by letter, word, or chunk with the ability to activate links and
  report additional context and role information per chunk.

  @ivar details: Details collected from traversed nodes, not yet announced 
  @type details: list of dict
  '''
  def __init__(self, *args, **kwargs):
    '''
    Initializes an instance.

    See parent instance variables for parameter descriptions.
    '''
    Text.TextReading.__init__(self, *args, **kwargs)
    self.details = []

  def _GetSpeakableIndex(self):
    return None

  def _GetSoundableRole(self, details):
    '''
    Maps a raw role to a sound role.

    @param details: Dictionaries of role, state, and description information
    @type details: list of dict
    @return: Sound file and container sound file, or None in either slot
    @rtype: 2-tuple of string
    '''
    has_details = False
    summary_sound = None
    content_sound = None
    for detail in details:
      if has_details and detail['trivial']:
        continue
      role = detail['role']
      try:
        # see if we have a sound for this role
        role_sound = Output.ISound(self).Role(role)
      except KeyError:
        pass
      else:
        if summary_sound is None:
          # prefer to use the summary sound to indicate role
          summary_sound = role_sound
        else:
          # if we already have a summary sound
          if content_sound is not None:
            # and a content sound, move the content sound to the summary
            summary_sound = content_sound
          # and store this new sound as the content sound
          content_sound = role_sound
        # at least one sound collected
        has_details = True
    return summary_sound, content_sound

  def _GetSpeakableRole(self, details):
    '''
    Maps a raw role to a speakable role.

    @param details: Dictionaries of role, state, and description information
    @type details: list of dict
    @return: Speakable role
    @rtype: string
    '''
    has_details = False
    result = []
    for detail in details:
      if has_details and detail['trivial']: 
        continue
      role = detail['role']

      try:
        role = HEADING_MAP[role] + ' heading'
      except KeyError:
        pass

      # see if we have extra information about the state
      state = detail['state']
      if role == 'link':
        if 'traversed' in state:
          role = 'visited link'
        else:
          role = 'unvisited link'

      # store role and set details to true so we don't count trivials
      result.append(role)
      has_details = True

    return role

  def _GetSpeakableDescription(self, details):
    '''
    Gets a speakable string of all detail descriptions.

    @param details: Dictionaries of role, state, and description information
    @type details: list of dict
    @return: Text string of comma separated details
    @rtype: string
    '''
    summary_speech = []
    # build full description from all details
    summary_speech = [detail['description'] for detail in details 
                      if detail['description']]
    # build a string
    summary_speech = ', '.join(summary_speech)
    return summary_speech

  def _GetSeekablePredicate(self, key):
    '''
    Maps a raw character to a seekable role.

    @param key: Character pressed
    @type key: string
    @return: Callable predicate for seeking assuming 2 string inputs of role
      and state
    @rtype: callable
    @raise KeyError: When no predicate defined for given key
    '''
    return SEEK_MAP[key]

  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the name of the text control, the current word or chunk (optional),
    and the current position.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    details = IDetailable(self.model).GetInheritedFields()
    summary_sound, content_sound = self._GetSoundableRole(details)
    m = IText(self.model)
    p = Output.Packet(self, message)
    summary_speech = self._GetSpeakableDescription(details)
    if not summary_speech:
      summary_speech = None

    if Config.say_on_focus == 'word':
      text = m.GetWordText(IText.CURR)
      p.AddMessage(speech='%s' % text, person=Output.CONTENT)
      p.AddMessage(speech=summary_speech, sound=content_sound or summary_sound,
                   person=Output.SUMMARY)
      return p
    elif Config.say_on_focus == 'chunk':
      if len(m.GetChunkText(IText.TO_END)) == 0:
        p.AddMessage(sound=Output.ISound(self).State('last'), 
                     person=Output.CONTENT)
        p.AddMessage(speech=summary_speech, 
                     sound=content_sound or summary_sound,
                   person=Output.SUMMARY)
        return p
      else:
        packets = self.OutNextChunkByRead(message, False)
        packets[0].AddMessage(speech=summary_speech, 
                              sound=content_sound or summary_sound,
                   person=Output.SUMMARY)
        return packets
    else:
      p.AddMessage(speech=summary_speech, sound=content_sound or summary_sound,
                   person=Output.SUMMARY)
      p.AddMessage(speech='', person=Output.CONTENT)
      return p
    
  def OutChunkByChunk(self, message):
    '''
    Speaks the entire chunk. Plays the spelling sound and any sound indicating
    the role of the current chunk.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    summary_speech = self._GetSpeakableDescription(self.details)
    summary_sound, content_sound = self._GetSoundableRole(self.details)
    m = IText(self.model)

    packets = []
    utters = self._SplitChunk(m.GetChunkText(IText.CURR))
    for u in utters:
      p = Output.Packet(self, message)
      p.AddMessage(speech=u, spell=self.spell, person=Output.CONTENT)
      packets.append(p)
      message = None
    if not summary_speech:
      # needed to avoid empty string error foolishness
      summary_speech = None
    packets[0].AddMessage(speech=summary_speech, sound=content_sound or
                          summary_sound, person=Output.SUMMARY)
    return packets

  # these are all the same in this subclass
  OutPrevChunkByChunk = OutChunkByChunk
  OutNextChunkByChunk = OutChunkByChunk
  OutThisChunkByChunk = OutChunkByChunk

  def OutChunkByWord(self, message):
    '''
    Speaks the current word. Plays the spelling sound and any sound indicating
    the role of the current chunk.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message, Output.NARRATOR)
    p.AddMessage(speech=m.GetWordText(IText.CURR))
    packets = [p]
    p = self.OutChunkByChunk(message)
    packets.extend(p)
    return packets
    
  # these are all the same in this subclass
  OutPrevChunkByWord = OutChunkByWord
  OutNextChunkByWord = OutChunkByWord

  def OutChunkByChar(self, message):
    '''
    Speaks the current character and the current chunk if the caret just entered
    that chunk. Plays the next chunk sound and the mispelling sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    curr = m.GetCharText(IText.CURR)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=curr)
    p2 = self.OutChunkByChunk(message)
    packets = [p1]
    packets.extend(p2)
    return packets

  # these are all the same in this subclass
  OutPrevChunkByChar = OutChunkByChar
  OutNextChunkByChar = OutChunkByChar

  def _NavToNextText(self):
    '''
    Moves ahead to the next chunk containing content.

    @return: Caret object for the latest move
    @rtype: L{Text.CaretDetails}
    '''
    it = IText(self.model)
    while 1:
      caret = it.NextChunk(True)
      if caret.AtEnd:
        # if at end of text, break
        return caret
      self.details.append(IDetailable(self.model).GetFields())
      if it.GetChunkText().strip():
        # if chunk is not empty, break
        return caret

  def _NavToPrevText(self):
    '''
    Moves back to the previous chunk containing content. Does consider the
    current chunk.

    @return: Caret object for the latest move
    @rtype: L{Text.CaretDetails}
    '''
    it = IText(self.model)
    while 1:
      caret = it.PrevChunk()
      if caret.AtStart:
        return caret
      self.details.append(IDetailable(self.model).GetFields())
      if it.GetChunkText().strip():
        # if chunk is not empty, break
        return caret       

  def OnLow(self, message):
    '''
    Moves the virtual caret to the beginning of the next chunk.

    Calls OutNextChunkByChunk or OutEndOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Number of places the virtual caret moved
    @rtype: number
    '''
    caret = self._NavToNextText()
    if caret.AtEnd:
      # if at end of text, break
      p = self.OutEndOfText(message)
    else:
      # if chunk is non-empty, report it and its details
      p = self.OutNextChunkByChunk(message)
    # reset details
    self.details = []
    self.Output(self, p)

  def OnHigh(self, message):
    '''
    Moves the virtual caret to the beginning of this or the previous chunk.

    Calls OutPrevChunkByChunk, OutThisChunkByChunk, or OutStartOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    caret = self._NavToPrevText()
    if caret.AtStart:
      # if at end of text, break
      p = self.OutStartOfText(message)
    elif caret.NewChunk:
      # if previous chunk is non-empty, report it and its details
      p = self.OutPrevChunkByChunk(message)
    else:
      # the caret moved to the start of this chunk
      p = self.OutThisChunkByChunk(message)
    # reset details
    self.details = []
    self.Output(self, p)
  
  def OnPrevHigh(self, message):
    '''
    Moves the virtual caret to the beginning of this chunk.

    Calls OutThisChunkByChunk or OutStartOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    caret = IText(self.model).MoveStartChunk()
    if caret.AtStart:
      # the caret is at the beginning of the text
      p = self.OutStartOfText(message)
    else:
      # the caret moved to the start of this chunk
      p = self.OutNextWord(message)
    self.Output(self, p)

  def OnPrevLow(self, message):
    '''
    Moves the virtual caret to the end of this chunk.

    Calls OutPrevWord or OutEndOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    caret = IText(self.model).MoveEndChunk()
    if caret.AtEnd:
      # the caret is at the end of the text
      p = self.OutEndOfText(message)
    else:
      # the caret moved to the end of this chunk
      p = self.OutPrevWord(message)
    self.Output(self, p)

  def OnNextMid(self, message):
    '''
    Moves the virtual caret to the next character.

    Calls OutNextChar, OutNextChunkByChar, or OutEndOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Number of places the virtual caret moved
    @rtype: number
    '''
    it = IText(self.model)
    while 1:
      caret = it.NextChar()
      if caret.AtEnd:
        # if at end of text, break
        p = self.OutEndOfText(message)
        break
      elif caret.NewChunk:
        if not it.GetChunkText().strip():
          # if chunk is empty, append chunk details to list
          self.details.append(IDetailable(self.model).GetFields())
        else:
          # if chunk is non-empty, report it and its details
          self.details.append(IDetailable(self.model).GetFields())
          p = self.OutNextChunkByChar(message)
          break
      else:
        p = self.OutNextChar(message)
        break
    # reset details
    self.details = []
    self.Output(self, p)

  def OnPrevMid(self, message):
    '''
    Moves the virtual caret to the previous character.

    Calls OutPrevChar, OutPrevChunkByChar, or OutStartOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Number of places the virtual caret moved
    @rtype: number
    '''
    it = IText(self.model)
    while 1:
      caret = it.PrevChar()
      if caret.AtStart:
        # if at end of text, break
        p = self.OutStartOfText(message)
        break
      elif caret.NewChunk:
        if not it.GetChunkText().strip():
          # if chunk is empty, append chunk details to list
          self.details.append(IDetailable(self.model).GetFields())
        else:
          # if chunk is non-empty, report it and its details
          self.details.append(IDetailable(self.model).GetFields())
          p = self.OutPrevChunkByChar(message)
          break
      else:
        p = self.OutPrevChar(message)
        break
    # reset details
    self.details = []
    self.Output(self, p)

  def OnNextMidMod(self, message):
    '''
    Moves the virtual caret to the next word.

    Calls OutNextWord, OutNextChunkByWord, or OutEndOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Number of places the virtual caret moved
    @rtype: number
    '''
    it = IText(self.model)
    while 1:
      caret = it.NextWord()
      if caret.AtEnd:
        # if at end of text, break
        p = self.OutEndOfText(message)
        break
      elif caret.NewChunk:
        if not it.GetChunkText().strip():
          # if chunk is empty, append chunk details to list
          self.details.append(IDetailable(self.model).GetFields())
        else:
          # if chunk is non-empty, report it and its details
          self.details.append(IDetailable(self.model).GetFields())
          p = self.OutNextChunkByWord(message)
          break
      else:
        p = self.OutNextWord(message)
        break
    # reset details
    self.details = []
    self.Output(self, p)

  def OnPrevMidMod(self, message):
    '''
    Moves the virtual caret to the previous word.

    Calls OutPrevWord, OutPrevChunkByWord, or OutEndOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Number of places the virtual caret moved
    @rtype: number
    '''
    it = IText(self.model)
    while 1:
      caret = it.PrevWord()
      if caret.AtStart:
        # if at end of text, break
        p = self.OutStartOfText(message)
        break
      elif caret.NewChunk:
        if not it.GetChunkText().strip():
          # if chunk is empty, append chunk details to list
          self.details.append(IDetailable(self.model).GetFields())
        else:
          # if chunk is non-empty, report it and its details
          self.details.append(IDetailable(self.model).GetFields())
          p = self.OutPrevChunkByWord(message)
          break
      else:
        p = self.OutPrevWord(message)
        break
    # reset details
    self.details = []
    self.Output(self, p)

  def OutCurrentItem(self, message):
    '''
    Outputs the curent word and its position in the text.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), person=Output.CONTENT, 
                 spell=self.spell)
    #p.AddMessage(speech=self.GetSpeakableIndex(), person=Output.SUMMARY)
    return p
    
  def OnText(self, message):
    '''
    Navigates to the next element having a role matching the hotkey pressed
    
    Plays OutNotImplemented, OutWrapSeekItem, OutSeekItem, or OutNoSeekItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}    
    '''
    # map key to element type
    try:
      pred = self._GetSeekablePredicate(message.Char.lower())
    except KeyError:
      # not a valid seek
      return

    # figure out forward or backward
    forward = (message.Char != message.Char.upper())

    p = None
    try:
      r = ISeekable(self.model).SeekToItem(pred, forward)
    except NotImplementedError:
      p = self.OutNotImplemented(message, 
                                 'Seeking by element is not available.')
    else:
      if r == True:
        p = self.OutWrapSeekItem(message, message.Char)
      elif r == False:
        it = IText(self.model)
        if not it.GetChunkText().strip():
          # make sure we're on a node with some text, else store details and
          # move ahead to the real content
          self.details.append(IDetailable(self.model).GetFields())
          caret = self._NavToNextText()
          if caret.AtEnd:
            # no content after the match, weird case
            p = self.OutEndOfText(message)    
        if p is None:
          self.details.append(IDetailable(self.model).GetFields())
          # check to ensure we didn't do an end of text announcement
          p = self.OutSeekItem(message, message.Char)
      else:
        self.details.append(IDetailable(self.model).GetFields())
        p = self.OutNoSeekItem(message, message.Char)
    self.details = []
    self.Output(self, p)

  def OutSeekItem(self, message, text):
    '''
    Speaks the current chunk, plays any role related sounds, and plays the 
    misspelled sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    summary_speech = self._GetSpeakableDescription(self.details)
    summary_sound, content_sound = self._GetSoundableRole(self.details)
    m = IText(self.model)

    packets = []
    utters = self._SplitChunk(m.GetChunkText(IText.CURR))
    for u in utters:
      p = Output.Packet(self, message)
      p.AddMessage(speech=u, spell=self.spell, person=Output.CONTENT)
      packets.append(p)
      message = None
    if not summary_speech:
      # needed to avoid empty string error foolishness
      summary_speech = None
    packets[0].AddMessage(speech=summary_speech, sound=content_sound or
                          summary_sound, person=Output.SUMMARY)
    
    p = Output.Packet(self, message, Output.NARRATOR)
    p.AddMessage(speech=text, letters=True)
    packets.append(p)
    return packets

  def OutSearchItem(self, message, text):
    '''
    Speaks the current word and plays any role related sounds.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    # collect all role information up the ancestor chain
    details = IDetailable(self.model).GetInheritedFields()
    summary_sound, content_sound = self._GetSoundableRole(details)
    summary_speech = self._GetSpeakableDescription(details)

    m = IText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), 
                 spell=self.spell, person=Output.CONTENT)
    if not summary_speech:
      # needed to avoid empty string error foolishness
      summary_speech = None
    p.AddMessage(speech=summary_speech, sound=content_sound or
                 summary_sound, person=Output.SUMMARY)
    
    p2 = Output.Packet(self, message, Output.NARRATOR)
    p2.AddMessage(speech=text, letters=True)
    return p, p2

  @Support.generator_method('Hypertext')
  def OutDetailCurrent_gen(self, message):
    '''
    Speaks the current word, spells it, and the states its position in the text.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    yield p
    #p = Output.Packet(self, message, listen=True, name='details')
    #p.AddMessage(speech=self.GetSpeakableIndex(), person=Output.SUMMARY)
    #yield p
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech=m.GetWordText(IText.CURR), person=Output.CONTENT,
                 letters=True)
    yield p

    # collect all role information up the ancestor chain
    details = IDetailable(self.model).GetInheritedFields()
    summary_sound, content_sound = self._GetSoundableRole(details)
    summary_speech = self._GetSpeakableRole(details)
    # speak and play role information
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech=summary_speech, sound=content_sound or summary_sound, 
                 person=Output.SUMMARY)
    yield p

    # speak text details
    summary_speech = self._GetSpeakableDescription(details)
    for text in summary_speech.split(', '):
      if text:
        p = Output.Packet(self, message, listen=True, name='details')
        p.AddMessage(speech=text, person=Output.SUMMARY)
        yield p

  def OnSayDone(self, message):
    '''
    Advances the virtual caret ahead during reading.

    Calls OutEndOfText or OutNextChunkByRead

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if not self.has_focus:
      return
    if message.Name != 'read:end-of-chunk':
      # not really the end of the chunk, just the end of a sentence
      return self.OnSayWord(message)
    caret = self._NavToNextText()
    if caret.AtEnd:
      p = self.OutEndOfText()
    else:
      p = self.OutNextChunkByRead(message, True)
    self.details = []
    self.Output(self, p)

  def OutNextChunkByRead(self, message, next):
    '''
    Speaks all text in the current chunk. Plays the next chunk sound and the
    mispelling sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param next: Attempt to play the next chunk sound?
    @type next: boolean
    @return: Packets containing messages to be read
    @rtype: list of L{Output.Messages.OutboundPacket}
    '''
    packets = []
    # get all text from here to end of chunk
    m = IText(self.model)
    text = m.GetChunkText(IText.TO_END)
    # get role sounds
    summary_sound, content_sound = self._GetSoundableRole(self.details)
    # split on sentence boundaries to speed rendering
    raw_chunks = text.split('. ')
    # put the stripped characters back in
    chunks = [c+'. ' for c in raw_chunks[:-1]]
    chunks.append(raw_chunks[-1])
    p = Output.Packet(self, None)
    name = None
    for i, c in enumerate(chunks):
      if (i == len(chunks)-1):
        # put a name on the last chunk so we can identify it
        name = 'read:end-of-chunk'
      p.AddMessage(speech=c, person=Output.CONTENT,
                   listen=True, name=name)
      if (i == 0) and next:
        p.AddMessage(sound=content_sound or summary_sound, person=Output.SUMMARY)
      packets.append(p)
      p = Output.Packet(self, None)
    return packets
