'''
Defines classes for handling text interaction patterns, namely reading and
editing.

@todo: handle autocomplete on text entry; breaks with backspace/delete?
@todo: handle text selection?

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from Interface import IEditableText, IText
import Base, Output, Support, Config

class TextReading(Base.Control):
  '''
  Navigable by letter, word, or chunk.

  @ivar spell: Should words be spell checked?
  @type spell: boolean
  '''
  def __init__(self, parent, model, name='', spell=True, default_name='text'):
    '''
    Initializes an instance.

    See instance variables for parameter descriptions.
    '''
    Base.Control.__init__(self, parent, model, name, default_name)
    self.spell = spell

  def _SplitChunk(self, text):
    '''
    @param text: Large block of text
    @type text: string
    @return: List of sentence-like utterences
    @rtype: list
    '''
    # split on sentence boundaries to speed rendering
    raw_chunks = text.split('. ')
    # put the stripped characters back in
    chunks = [c+'. ' for c in raw_chunks[:-1]]
    chunks.append(raw_chunks[-1])
    return chunks

  def _GetSpeakableSize(self):
    '''
    @return: Size of text expressed in terms of read time.
    @rtype: string
    '''
    t = self._GetTime()
    it = round(t)
    # report in seconds if less than a minute
    if it >= 1.0:
      s = '%d minutes' % it
    elif round(t*60) > 0:
      s = '%d seconds' % round(t*60)
    else:
      s = ''
    return s

  def _GetSpeakableIndex(self):
    '''
    @return: Position in text expressed in terms of time out of total time
    @rtype: string
    '''
    # don't say anything if there is negligible text
    ss = self._GetSpeakableSize()
    if ss == '': return ''
    # get time to speak all previous text
    word_count = IText(self.model).GetWordCount(False)
    t = Output.TimeToSpeak(word_count)
    it = round(t)
    # report in seconds if less than a minute
    if it >= 1.0:
      s = '%d minutes into %s' % (it, ss)
    else:
      s = '%d seconds into %s' % (round(t*60), ss)
    return s

  def _GetTime(self):
    '''
    @return: Size of text in minutes to read
    @rtype: float
    '''
    return Output.TimeToSpeak(IText(self.model).GetWordCount())

  def OnActivate(self, message, auto_focus):
    '''
    Ensures the control is ready.

    Plays OutIntroduction.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Is the control ready for interaction.
    @rtype: boolean
    '''
    if super(TextReading, self).OnActivate(message, auto_focus):
      p = self.OutIntroduction(message, auto_focus)
      self.Output(self, p)
      return True
    else:
      return False

  def OnRead(self, message):
    '''
    Reads all text continuously.

    @todo: this still seems to get stuck on occassion when reading hypertext

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = self.OutNextChunkByRead(message, False)
    self.Output(self, p)

  def OnSayWord(self, message):
    '''
    Advances the virtual caret ahead during reading.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if self.has_focus:
      IText(self.model).MoveXChars(message.Difference)
      #print IText(self.model).Chunk.GetCurrentWordBounds()

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
    it = IText(self.model)
    caret = it.NextChunk()
    if caret.AtEnd:
      p = self.OutEndOfText(None)
    else:
      p = self.OutNextChunkByRead(message, True)
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
    # break chunk into utterences
    chunks = self._SplitChunk(text)
    p = Output.Packet(self, None)
    name = None
    for i, c in enumerate(chunks):
      if (i == len(chunks)-1):
        # put a name on the last chunk so we can identify it
        name = 'read:end-of-chunk'
      p.AddMessage(speech=c, person=Output.CONTENT,
                   listen=True, spell=self.spell, name=name)
      if (i == 0) and next:
        p.AddMessage(sound=Output.ISound(self).Action('next'),
                     person=Output.SUMMARY)
      packets.append(p)
      p = Output.Packet(self, None)
    return packets

  def OnMoreInfo(self, message):
    '''
    Gives more information about the current word.

    Calls OutDetailCurrent.

    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = self.OutDetailCurrent(message)
    self.Output(self, p)

  def OnLow(self, message):
    '''
    Moves the virtual caret to the beginning of the next chunk.

    Calls OutNextChunkByChunk or OutEndOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Number of places the virtual caret moved
    @rtype: number
    '''
    caret = IText(self.model).NextChunk(True)
    if caret.AtEnd:
      # the caret is at the end of the text
      p = self.OutEndOfText(message)
    else:
      # the caret moved to the next chunk
      p = self.OutNextChunkByChunk(message)
    self.Output(self, p)

  def OnHigh(self, message):
    '''
    Moves the virtual caret to the beginning of this or the previous chunk.

    Calls OutPrevChunkByChunk, OutThisChunkByChunk, or OutStartOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    caret = IText(self.model).PrevChunk()
    if caret.NewChunk:
      # the caret is at the start of the previous chunk
      p = self.OutPrevChunkByChunk(message)
    elif caret.AtStart:
      # the caret is at the beginning of the text
      p = self.OutStartOfText(message)
    else:
      # the caret moved to the start of this chunk
      p = self.OutThisChunkByChunk(message)
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
    # move ahead one character
    caret = IText(self.model).NextChar()
    if caret.NewChunk:
      # the caret moved into the next chunk
      p = self.OutNextChunkByChar(message)
    elif caret.AtEnd:
      # the caret is at the end of the text
      p = self.OutEndOfText(message)
    else:
      # the caret moved ahead one character in the current chunk
      p = self.OutNextChar(message)
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
    # move back one character
    caret = IText(self.model).PrevChar()
    if caret.NewChunk:
      # the caret moved into the previous chunk
      p = self.OutPrevChunkByChar(message)
    elif caret.AtStart:
      # the caret is at the beginning of the text
      p = self.OutStartOfText(message)
    else:
      # the caret moved back one character in the current chunk
      p = self.OutPrevChar(message)
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
    # move ahead one word
    caret = IText(self.model).NextWord()
    if caret.NewChunk:
      # the caret moved into the next chunk
      p = self.OutNextChunkByWord(message)
    elif caret.AtEnd:
      # the caret is at the end of the text
      p = self.OutEndOfText(message)
    else:
      # the caret moved ahead one word in the current chunk
      p = self.OutNextWord(message)
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
    # move back one word
    caret = IText(self.model).PrevWord()
    if caret.NewChunk:
      # the caret moved into the previous chunk
      p = self.OutPrevChunkByWord(message)
    elif caret.AtStart:
      # the caret is at the beginning of the text
      p = self.OutStartOfText(message)
    else:
      # the caret moved back one word in the current chunk
      p = self.OutPrevWord(message)
    self.Output(self, p)

  def OutEndOfText(self, message):
    '''
    Plays the end of text sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('last'), person=Output.SUMMARY)
    return p

  def OutStartOfText(self, message):
    '''
    Plays the start of text sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('first'),
                 person=Output.SUMMARY)
    return p

  def OutPrevChar(self, message):
    '''
    Speaks the current character and the previous word if the caret just entered
    that word. Plays the mispelling sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    curr, prev = m.GetCharText(IText.CURR), m.GetCharText(IText.PREV)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=curr)
    p2 = Output.Packet(self, message)
    if curr == ' ' and prev != ' ':
      p2.AddMessage(speech=m.GetWordText(IText.PREV), spell=self.spell,
                    person=Output.CONTENT)
    return (p1, p2)

  def OutNextChar(self, message):
    '''
    Speaks the current character and the next word if the caret just entered
    that word. Plays the mispelling sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    curr, prev = m.GetCharText(IText.CURR), m.GetCharText(IText.PREV)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=curr)
    p2 = Output.Packet(self, message)
    if curr != ' ' and prev == ' ':
      p2.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                   person=Output.CONTENT)
    return (p1, p2)

  def OutPrevWord(self, message):
    '''
    Speaks the current word and plays the mispelling sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    return p

  def OutNextWord(self, message):
    '''
    Speaks the current word and plays the mispelling sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    return p

  def OutDeadLong(self, message):
    '''
    Outputs a message stating the text is not available.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    # the control is missing, inform the user
    p = Output.Packet(self, message)
    p.AddMessage(speech='The %s text is not available' % self.Name,
                 person=Output.SUMMARY)
    return p

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
    m = IText(self.model)
    p = Output.Packet(self, message)
    s = '%s, %s' % (self.Name, self._GetSpeakableIndex())
    if Config.say_on_focus == 'word':
      text = m.GetWordText(IText.CURR)
      p.AddMessage(speech='%s' % text, person=Output.CONTENT)
      p.AddMessage(speech=s, sound=Output.ISound(self).Action('start'),
                   person=Output.SUMMARY)
      return p
    elif Config.say_on_focus == 'chunk':
      if len(m.GetChunkText(IText.TO_END)) == 0:
        p.AddMessage(sound=Output.ISound(self).State('last'), 
                     person=Output.CONTENT)
        p.AddMessage(speech=s, sound=Output.ISound(self).Action('start'),
                     person=Output.SUMMARY)
        return p
      else:
        packets = self.OutNextChunkByRead(message, False)
        packets[0].AddMessage(speech=s, 
                              sound=Output.ISound(self).Action('start'), 
                              person=Output.SUMMARY)
        return packets
    else:
      p.AddMessage(speech=s, sound=Output.ISound(self).Action('start'),
                   person=Output.SUMMARY)
      p.AddMessage(speech='', person=Output.CONTENT)
      return p

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
    p.AddMessage(speech=m.GetWordText(IText.CURR), person=Output.CONTENT)
    p.AddMessage(speech=self._GetSpeakableIndex(), person=Output.SUMMARY)
    return p

  @Support.generator_method('Text')
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
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech=self._GetSpeakableIndex(), person=Output.SUMMARY)
    yield p
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech=m.GetWordText(IText.CURR), person=Output.CONTENT,
                 letters=True)
    yield p

  def OutPrevChunkByChar(self, message):
    '''
    Speaks the current character and the current chunk if the caret just entered
    that chunk. Plays the previous chunk sound and the mispelling sound if
    desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=m.GetCharText(IText.CURR))
    p2 = Output.Packet(self, message)
    if m.GetCharText(IText.PREV) != ' ':
       p2.AddMessage(speech=m.GetWordText(IText.PREV), spell=self.spell,
                    person=Output.CONTENT)
    p2.AddMessage(sound=Output.ISound(self).Action('previous'),
                   person=Output.SUMMARY)
    return (p1, p2)

  def OutNextChunkByChar(self, message):
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
    p2 = Output.Packet(self, message)
    if curr != ' ':
      p2.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                   person=Output.CONTENT)
    p2.AddMessage(sound=Output.ISound(self).Action('next'),
                   person=Output.SUMMARY)
    return (p1, p2)

  def OutPrevChunkByWord(self, message):
    '''
    Speaks the current chunk. Plays the previous chunk sound and the mispelling
    sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('previous'),
                 person=Output.SUMMARY)
    return p

  def OutNextChunkByWord(self, message):
    '''
    Speaks the current chunk. Plays the next chunk sound and the mispelling
    sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('next'),
                 person=Output.SUMMARY)
    return p

  def OutPrevChunkByChunk(self, message):
    '''
    Speaks the current chunk. Plays the previous chunk sound and the mispelling
    sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    packets = []
    m = IText(self.model)
    # split into multile utterances
    utters = self._SplitChunk(m.GetChunkText(IText.CURR))
    for u in utters:
      p = Output.Packet(self, message)
      p.AddMessage(speech=u, spell=self.spell, person=Output.CONTENT)
      packets.append(p)
      message = None
    # add summary info to first packet
    packets[0].AddMessage(sound=Output.ISound(self).Action('previous'),
                          person=Output.SUMMARY)
    return packets

  def OutThisChunkByChunk(self, message):
    '''
    Speaks the current chunk. Plays the next chunk sound and the mispelling 
    sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    packets = []
    m = IText(self.model)
    # split into multile utterances
    utters = self._SplitChunk(m.GetChunkText(IText.CURR))
    for u in utters:
      p = Output.Packet(self, message)
      p.AddMessage(speech=u, spell=self.spell, person=Output.CONTENT)
      packets.append(p)
      message = None
    return packets

  def OutNextChunkByChunk(self, message):
    '''
    Speaks the current word. Plays the next chunk sound and the mispelling sound
    if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    packets = []
    m = IText(self.model)
    # split into multile utterances
    utters = self._SplitChunk(m.GetChunkText(IText.CURR))
    for u in utters:
      p = Output.Packet(self, message)
      p.AddMessage(speech=u, spell=self.spell, person=Output.CONTENT)
      packets.append(p)
      message = None
    # add summary info to first utterance packet
    packets[0].AddMessage(sound=Output.ISound(self).Action('next'),
                          person=Output.SUMMARY)
    return packets

  def OutWhereAmI(self, message):
    '''
    Outputs the name and sound of the text reading.

    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Base.Control.OutWhereAmI(self, message)
    s = 'reading the %s text' % self.Name
    p.AddMessage(speech=s, person=Output.SUMMARY,
                 sound=Output.ISound(self).Action('start'))
    return p

  def OutChange(self, message):
    '''
    Speaks either the new text value if it is short or the length of the text
    if it is long.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    sec = self._GetTime()*60
    # speak a summary if the text is longer than 5 seconds
    if sec > 5:
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   speech='%s of text in %s' % (self._GetSpeakableSize(),
                                                self.Name))
    # speak all the text if there is some
    elif sec > 0:
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   speech='%s in %s' % (IText(self.model).GetAllText(),
                                        self.Name))
    # say there is no text otherwise
    else:
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   speech='%s has no text' % self.Name)
    return p

  def OutSeekItem(self, message, text):
    '''
    Speaks the current word and plays the misspelled sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    p.AddMessage(speech=self._GetSpeakableIndex(), person=Output.SUMMARY)
    p2 = Output.Packet(self, message, Output.NARRATOR)
    p2.AddMessage(speech=text, letters=True)
    return p, p2

  OutSearchItem = OutSeekItem

class TextEntry(TextReading):
  '''
  Editable, plain text.
  '''
  def __init__(self, parent, model, name='', spell=True):
    super(TextEntry, self).__init__(parent, model, name, spell,
                                    default_name='text entry')

  def OnDelete(self, message):
    '''
    Deletes the current character.

    Calls OutSpaceDeleted, OutCharDeleted, OutChunkJoin, or OutEndOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    m = IEditableText(self.model)
    caret = m.DeleteNext()
    if caret.NewWord:
      if caret.Joined:
        # two words joined
        p = self.OutWordJoin(message, caret.Char)
      else:
        # touching a new word
        p = self.OutSpaceDeleted(message, caret.Char)
    elif caret.AtEnd:
      # the caret is at the end of the text
      p = self.OutEndOfText(message)
    elif caret.NewChunk:
      # two chunks joined
      p = self.OutChunkJoin(message, caret.Char)
    else:
      # a char was deleted
      p = self.OutCharDeleted(message, caret.Char)
    self.NotifyAboutChange()
    self.Output(self, p)

  def OnBackspace(self, message):
    '''
    Deletes the previous character.

    Calls OutSpaceDeleted, OutCharDeleted, OutChunkJoin, or OutStartOfText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    m = IEditableText(self.model)
    caret = m.DeletePrev()
    if caret.NewWord:
      if caret.Joined:
        # two words joined
        p = self.OutWordJoin(message, caret.Char)
      else:
        # touching a new word
        p = self.OutPrevSpaceDeleted(message, caret.Char)
    elif caret.AtStart:
      # the caret is at the start of the text
      p = self.OutStartOfText(message)
    elif caret.NewChunk:
      # two chunks joined
      p = self.OutChunkJoin(message, caret.Char)
    else:
      # a char was deleted
      p = self.OutPrevCharDeleted(message, caret.Char)
    self.NotifyAboutChange()
    self.Output(self, p)

  def OnText(self, message):
    '''
    Inserts a character to the text.

    Calls OutWordSplit, OutNewWord, or OutNewChar.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    caret = IEditableText(self.model).InsertChar(message.Char)
    if caret.Split:
      # a word split in two
      p = self.OutWordSplit(message)
    elif caret.NewWord:
      # a new word was added
      p = self.OutNewWord(message)
    else:
      # a character was added
      p = self.OutNewChar(message)
    self.NotifyAboutChange()
    self.Output(self, p)
    
  def OnMemoryInsert(self, message):
    '''
    Inserts a chunk of text from the memory menu in the text.

    Calls OutInsertText.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    ie = IEditableText(self.model)
    ie.InsertText(message.Text)
    # get the chunk before changing chunks
    text = ie.GetChunkText(IText.FROM_START)
    p1 = self.OutInsertText(message, text)
    # now insert a chunk
    ie.InsertChunk()
    # get first word of next chunk
    word = ie.GetWordText(IText.CURR)
    p2 = self.OutNewChunk(None, word)
    self.Output(self, p1)#(p1, p2))

  def OnEnter(self, message):
    '''
    Inserts a new line in the text.

    Calls OutNewChunk or OutChunkSplit.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    m = IEditableText(self.model)
    # get the last word on the line before inserting the new line
    last_word = m.GetWordText(IText.PREV)
    caret = m.InsertChunk()
    if caret is None:
      # not a multiline textbox
      return
    if caret.Split:
      # a line split
      p = self.OutChunkSplit(message)
    else:
      # a new line was added
      p = self.OutNewChunk(message, last_word)
    self.NotifyAboutChange()
    self.Output(self, p)

  def OutWordJoin(self, message, c):
    '''
    Speaks the word formed from two joined words and plays the join sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param c: Deleted character
    @type c: string
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IEditableText(self.model)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=c)
    p2 = Output.Packet(self, message)
    p2.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                  person=Output.CONTENT)
    p2.AddMessage(sound=Output.ISound(self).Action('join-word'),
                  person=Output.SUMMARY)
    return p1, p2

  def OutWordSplit(self, message):
    '''
    Speaks the two words formed from a split word and plays the split sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IEditableText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.PREV)+' '+m.GetWordText(IText.CURR),
                 spell=self.spell, person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('split-word'),
                 person=Output.SUMMARY)
    return p

  def OutChunkJoin(self, message, c):
    '''
    Speaks the word formed from two joined chunks and plays the join chunk
    sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param c: Chunk separator character deleted
    @type c: string
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IEditableText(self.model)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=c)
    p2 = Output.Packet(self, message)
    p2.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                  person=Output.CONTENT)
    p2.AddMessage(sound=Output.ISound(self).Action('join-chunk'),
                  person=Output.SUMMARY)
    return p1, p2

  def OutChunkSplit(self, message):
    '''
    Speaks the two words formed from a split chunk and plays the split chunk
    sound.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IEditableText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('split-chunk'),
                 person=Output.SUMMARY)
    return p

  def OutSpaceDeleted(self, message, c):
    '''
    Speaks the next word and the space.

    @param c: Deleted character
    @type c: string
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IEditableText(self.model)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=c)
    p2 = Output.Packet(self, message)
    p2.AddMessage(speech=m.GetWordText(IText.CURR), spell=self.spell,
                 person=Output.CONTENT)
    return (p1, p2)

  def OutCharDeleted(self, message, c):
    '''
    Speaks the deleted character and the next character.

    @param c: Deleted character
    @type c: string
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.NARRATOR)
    p.AddMessage(speech=c)
    return p

  def OutPrevSpaceDeleted(self, message, c):
    '''
    Speaks the previous word and the deleted space. Plays the mispell sound
    if desired.

    @param c: Deleted character
    @type c: string
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IEditableText(self.model)
    p1 = Output.Packet(self, message, Output.NARRATOR)
    p1.AddMessage(speech=c)
    p2 = Output.Packet(self, message)
    p2.AddMessage(speech=m.GetWordText(IText.PREV), spell=self.spell,
                 person=Output.CONTENT)
    return (p1, p2)

  def OutPrevCharDeleted(self, message, c):
    '''
    Speaks the deleted character and the current character.

    @param c: Deleted character
    @type c: string
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.NARRATOR)
    p.AddMessage(speech=c)
    return p

  def OutNewChar(self, message):
    '''
    Speaks a newly added character.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    if Config.speak_chars:
      p = Output.Packet(self, message, Output.NARRATOR)
      p.AddMessage(speech=message.Char)
      return p

  def OutNewWord(self, message):
    '''
    Speaks a newly added word and plays the misspell sound if desired.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = IEditableText(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetWordText(IText.PREV), spell=self.spell,
                 person=Output.CONTENT)
    return p

  def OutNewChunk(self, message, word):
    '''
    Speaks the word at the end of the previous chunk. Plays the next chunk
    sound and the mispell sound if desired.

    @param word: Last word on the line before the newline
    @type word: string
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(speech=word, spell=self.spell, person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('next'),
                 person=Output.SUMMARY)
    return p

  def OutInsertText(self, message, text):
    '''
    Speaks the chunk around the inserted text.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text around the inserted chunk
    @type text: string
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message, Output.ACTIVE_PROG)
    p.AddMessage(speech=text, person=Output.ACTIVE_PROG, 
                 sound=Output.ISound(self).Action('start'))
    return p

  def OutChange(self, message):
    '''
    Speaks either the new text value if it is short or the length of the text
    if it is long long.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    # speak a summary if the text is longer than 5 seconds
    if self._GetTime()*60 > 5:
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   speech='%s of text in %s' % (self._GetSpeakableSize(),
                                                self.Name))
    # speak all the text otherwise
    elif IText(self.model).GetWordCount(all=False) > 0:
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   speech='%s in %s' % (IText(self.model).GetAllText(),
                                        self.Name))
    else:
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   speech='%s has no text' % (self.Name))
    return p

  def OutWhereAmI(self, message):
    '''
    Outputs the name and sound of the text entry.

    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Base.Control.OutWhereAmI(self, message)
    s = 'editing the %s text' % self.Name
    p.AddMessage(speech=s, person=Output.SUMMARY,
                 sound=Output.ISound(self).Action('start'))
    return p

if __name__ == '__main__':
  pass
