'''
Defines adapters for text types like labels, text boxes, and cacheable
hypertext.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import unicodedata
import re, pyAA
from Base import Adapter
from protocols import advise
from Constants import *
from Interface import *

# word separator
word_regex = re.compile('(^| )([^ ]+)($| )')

def GetAOText(ao):
  '''
  Read the text from the pyAA.AcessibleObject if possible.

  @todo: needs to check the ao role to see if the name should be used first
  instead of the value (e.g. for email addresses)
  '''
  if ao.GetRoleText() == "link":
    order = ['Name', 'Value']
  else:
    order = ['Value', 'Name']
  for attr in order:
    try:
      v = getattr(ao, attr)
      if v: return v # is not None condition changed
    except pyAA.Error:
      pass
    except AttributeError:
      pass
  return ''

class CaretDelta(object):
  '''
  Bag class defining a change in virtual caret position. Gives information about
  how many places the caret moved, if it moved into a new word/chunk, if it is
  at the start of all of the text or at the end, and if the move joined or split
  a word or chunk.

  @ivar Moved: Number of character places the caret moved
  @type Moved: integer
  @ivar NewWord: Did the caret move into a new or different word?
  @type NewWord: boolean
  @ivar NewChunk: Did the caret move into a new or different chunk?
  @type NewChunk: boolean
  @ivar InFirst: Is the caret in the first chunk?
  @type InFirst: boolean
  @ivar InLast: Is the caret in the last chunk?
  @type InLast: boolean
  @ivar AtEnd: Was the caret already at the end of all text?
  @type AtEnd: boolean
  @ivar AtStart: Was the caret already at the start of all text?
  @type AtStart: boolean
  @ivar Joined: Did two items join? (see NewItem to determine if word or chunk)
  @type Joined: boolean
  @ivar Split: Did two items split? (see NewItem to determine if word or chunk)
  @type Split: boolean
  '''
  def __init__(self, moved, first, last, start, end):
    self.Moved = moved
    self.InFirst = first
    self.InLast = last
    self.AtStart = start and first and not moved
    self.AtEnd = end and last
    self.Char = None
    self.NewItem = False
    self.NewChunk = False
    self.NewWord = False
    self.Joined = False
    self.Split = False

class Chunk(object):
  '''
  Unchangeable block of text, possibly a line or paragraph. Maintains a pointer
  to a virtual caret position so the chunk can be navigated by character or
  word.

  @ivar pos: Virtual caret position in characters
  @type pos: number
  @ivar text: All text in the chunk
  @type text: string
  '''
  def __init__(self, text=''):
    '''
    Initialize the object.

    @param text: Starting text for the chunk
    @type text: string
    '''
    self.text = text
    self.pos = 0

  def __repr__(self):
    '''Return the representation of a chunk as a string.'''
    return self.text

  def __eq__(self, other):
    '''
    Compares text held by this chunk to the text held by another chunk.

    @param other: Another chunk
    @type other: L{Chunk}
    '''
    return self.text == other.text

  def GetCurrentChar(self):
    '''
    @return: Character at the virtual caret position
    @rtype: string
    '''
    if self.pos >= self.Size:
      return None
    else:
      return self.text[self.pos]
  Char = property(GetCurrentChar)

  def GetPrevChar(self):
    '''
    @return: Character one behind the virtual caret position
    @rtype: string
    '''
    if self.pos > 0:
      return self.text[self.pos-1]
    else:
      return None
  PrevChar = property(GetPrevChar)

  def GetNextChar(self):
    '''
    @return: Character one beyond the virtual caret position
    @rtype: string
    '''
    if self.pos < self.Size-1:
      return self.text[self.pos+1]
    else:
      return None
  NextChar = property(GetNextChar)

  def GetSpeakableChar(self):
    '''
    @return: Speakable representation of the character at the virtual caret
    @rtype: string
    '''
    try:
      return self.text[self.pos]
    except:
      return ' '
  SpeakChar = property(GetSpeakableChar)

  def GetCurrentWordBounds(self):
    '''
    @return: Word start and end index within the chunk
    @rtype: 2-tuple of integer
    '''
    if self.Size == 0: return ''
    pos = self.pos-1
    # seek backward to the space between this word and the previous
    while self.GetCharAt(pos) not in [' ', None] and pos > 0:
      pos -= 1
    # search ahead to find the current word
    mo = word_regex.search(self.text, pos)
    if mo:
      return pos, mo.end(2)

  def GetCurrentWord(self):
    '''
    @return: Word the virtual caret is touching
    @rtype: string
    '''
    if self.Size == 0: return ''
    pos = self.pos-1
    # seek backward to the space between this word and the previous
    while self.GetCharAt(pos) not in [' ', None] and pos > 0:
      pos -= 1
    # search ahead to find the current word
    mo = word_regex.search(self.text, pos)
    if mo:
      return mo.group(2)
    else:
      return ''
  Word = property(GetCurrentWord)

  def GetPrevWord(self):
    '''
    @return: Word behind the virtual caret position
    @rtype: string
    '''
    if self.Size == 0:
      return ''
    pos = self.pos
    # seek back to the break between this word and the previous
    while self.GetCharAt(pos) not in [' ', None] and pos > 0:
      pos -= 1
    # search backwards past the break for the previous word
    mo = word_regex.search(self.text[::-1], self.Size - pos - 1)
    if mo:
      return mo.group(2)[::-1]
    else:
      return ''
  PrevWord = property(GetPrevWord)

  def GetSize(self):
    '''
    @return: Size of the chunk in characters
    @rtype: number
    '''
    return len(self.text)
  Size = property(GetSize)

  def GetIndex(self):
    '''
    @return: Index of the virtual caret within the chunk in characters
    @rtype: integer
    '''
    return self.pos
  Index = property(GetIndex)

  def IsAtStart(self):
    '''
    Checks if the caret is at the start of the chunk.

    @return: Is the virtual caret is at the start of the chunk?
    @rtype: boolean
    '''
    return self.pos == 0

  def IsAtEnd(self):
    '''
    Checks if the caret is at the end of the chunk.

    @return: Is the virtual caret is at the end of the chunk?
    @rtype: boolean
    '''
    return self.pos == self.Size

  def GetCharAt(self, i):
    '''
    Gets the character at the given position in the chunk.

    @param i: Position of the target character
    @type i: integer
    @return: Character if it exists, else None
    @rtype: None or string
    '''
    if i < self.Size and i > -1:
      return self.text[i]
    else:
      return None

  def GetFromBeginning(self):
    '''
    @return: Text from beginning of the chunk to current position
    @rtype: string
    '''
    return self.text[:self.pos]

  def GetToEnd(self):
    '''
    @return: Text from the current position to the end of the chunk
    @rtype: string
    '''
    return self.text[self.pos:]

  def FindNext(self, text, offset):
    '''
    Finds the next instance of the given text in this chunk. Gets the number of
    characters between the current position and the first character in the
    matching text if found. Returns None if not found.

    @param text: Text to find
    @type text: string
    @param offset: Offset from the current position at which to start searching
    @type offset: integer
    @return: Characters between the current position and the match or None
    @rtype: integer
    '''
    i = self.text[self.pos+offset:].lower().find(text.lower())
    if i == -1:
      return None
    else:
      return i+offset

  def FindPrev(self, text, offset):
    '''
    Finds the previous instance of the given text in this chunk. Gets the
    number of characters between the current position and the first character in
    the matching text if found. Returns None if not found.

    @param text: Text to find
    @type text: string
    @param offset: Offset from the current position at which to start searching
    @type offset: integer
    @return: Characters between the current position and the match or None
    @rtype: integer
    '''
    i = self.text[:self.pos+offset].lower().rfind(text.lower())
    if i == -1:
      return None
    else:
      return i-self.pos

  def MoveXChars(self, x):
    '''
    Moves the virtual caret the given number of characters ahead or back in the
    chunk. Snap to bounds.

    @param x: Number of characters to move
    @type x: integer
    @return: Number of places moved to reach new position from old position
    @rtype: integer
    '''
    p = self.pos + x
    if p < 0:
      # snap to the beginning
      p = self.pos
      self.pos = 0
      return p
    elif self.pos > self.Size:
      # snap to the end
      p = self.Size-self.pos
      self.pos = self.Size-1
      return p
    else:
      self.pos = p
      return x

  def MoveStart(self):
    '''
    Moves the virtual caret to the exact start of this chunk.

    @return: Number of places moved to reach new position from old position
    @rtype: integer
    '''
    p = -self.pos
    self.pos = 0
    return p

  def MoveEnd(self):
    '''
    Moves the virtual caret to the exact end of this chunk.

    @return: Number of places moved to reach new position from old position
    @rtype: integer
    '''
    p = self.pos
    self.pos = self.Size
    return self.Size-p

  def MoveFirstWordFromCurrent(self):
    '''
    Move the virtual caret to the start of the first word. Skips any initial
    whitespace in the chunk.

    @return: Number of places moved and the current virtual caret position
    @rtype: 2-tuple of integer
    '''
    p = self.pos
    s = self.MoveFirstWordFromStart()
    return p - s, p

  def MoveFirstWordFromStart(self):
    '''
    Move the virtual caret to the start of the first word. Skip any initial
    whitespace in the chunk.

    @return: Number of characters from the beginning of the chunk to first word
    @rtype: number
    '''
    self.pos = 0
    while self.Char == ' ' and self.pos < self.Size:
      self.pos += 1
    return self.pos

  def MoveLastWordFromEnd(self):
    '''
    Moves the virtual caret to the start of the last word. Skips any trailing
    whitespace in the chunk.

    @return: Number of characters from end of the chunk to start of last word
    @rtype: number
    '''
    self.pos = self.Size
    r, i = self.MovePrevWord()
    return i

  def MoveNextChar(self):
    '''
    Moves the virtual caret to the next character.

    @return: Number of places moved (1) or 0 if at the end of the chunk
    @rtype: integer
    '''
    if self.pos < self.Size:
      self.pos += 1
      return 1
    else:
      return 0

  def MovePrevChar(self):
    '''
    Moves the virtual caret to the previous character.

    @return: Number of places moved (-1) or 0 if at the start of the chunk
    @rtype: integer
    '''
    if self.pos > 0:
      self.pos -= 1
      return -1
    else:
      return 0

  def MoveNextWord(self):
    '''
    Moves the virtual caret to the start of the next word.

    @return: True and number of chars moved if word in this chunk
             False and the number of chars moved if word in next chunk
    @rtype: 2-tuple of boolean and integer
    '''
    mo = word_regex.search(self.text, self.pos+1)
    if mo:
      # a word was found
      p = mo.start() + 1
      diff = p - self.pos
      self.pos = p
      return True, diff
    else:
      # no word was found
      diff = self.Size - self.pos
      self.pos = self.Size
      return False, diff

  def MovePrevWord(self):
    '''
    Moves the virtual caret to the start of the previous word.

    @return: True and number of chars moved if word in this chunk
             False and the number of chars moved if word in previous chunk
    @rtype: 2-tuple of boolean and integer
    '''
    cs = self.text[::-1][self.Size - self.pos:]
    mo = word_regex.search(cs)
    if mo:
      # a word was found
      p = len(cs) - mo.end(2)
      diff = p - self.pos
      self.pos = p
      return True, diff
    else:
      # no word was found
      diff = -self.pos
      self.pos = 0
      return False, diff

class DynamicChunk(Chunk):
  '''Editable block of text.'''
  def GetSpeakableChar(self):
    '''
    @return: Speakable representation of the character at the virtual caret
    @rtype: string
    '''
    if self.pos == self.Size:
      return 'end line'
    elif ord(self.text[self.pos]) > 128:
      return 'space'
    else:
      return self.text[self.pos]
  SpeakChar = property(GetSpeakableChar)

  def Put(self, text):
    '''
    Adds a string to the chunk at the current virtual caret position.

    @param text: Text to add to the chunk
    @type text: string
    @return: Characters ahead and behind the inserted character
    @rtype: 2-tuple of string
    '''
    p = self.GetCharAt(self.pos-1)
    n = self.GetCharAt(self.pos)
    self.text = '%s%s%s' % (self.text[:self.pos], text, self.text[self.pos:])
    self.pos += len(text)
    return p, n

  def Delete(self):
    '''
    Deletes the character at the virtual caret position.

    @return: True and the character if it was deleted; False and None if the
             character does not exist in this chunk
    @rtype: 2-tuple of boolean and string or boolean and None
    '''
    if self.pos == self.Size:
      return False, None
    else:
      c = self.SpeakChar
      self.text = self.text[:self.pos]+self.text[self.pos+1:]
      return True, c

  def DeletePrev(self):
    '''
    Deletes the character one behind the virtual caret position.

    @return: True and the character if it was deleted; False and None if the
             character does not exist in this chunk
    @rtype: 2-tuple of boolean and string or boolean and None
    '''
    if self.pos == 0:
      return False, None
    else:
      self.pos -= 1
      return self.Delete()

  def Split(self):
    '''
    Splits this chunk into two chunks at the virtual caret position.

    @return: Text past the virtual caret position
    @rtype: L{DynamicChunk}
    '''
    mine = self.text[:self.pos]
    other = self.text[self.pos:]
    self.text = mine
    self.pos = self.Size
    return DynamicChunk(other)

  def Join(self, other):
    '''
    Appends this chunk to another chunk.

    @param other: Chunk to join with this chunk
    @type other: L{Chunk}
    @return: Were the chunks joined?
    @rtype: boolean
    '''
    if self.pos == self.Size:
      self.text += other.text
      return True
    else:
      return False

class TextLabel(Adapter):
  '''
  Simple static text label that stores all of its own data. Not adapted for
  any particular L{View}, but useful for resolving to a name string that can
  be used to identify a L{View}.

  @ivar template: Template to populate with the text label
  @type template: string
  '''
  advise(instancesProvide=[ILabel])

  def __init__(self, context, path, template='%s'):
    '''
    Initializes an instance.

    See instance variables for parameter descriptions.
    '''
    super(TextLabel, self).__init__(context, path)
    self.template = template

  def GetAllText(self):
    if self.Activate():
      return self.template % GetAOText(self.subject)
    else:
      return ''

  def __str__(self):
    return self.GetAllText()

class TextBox(Adapter):
  '''
  Simple, read-only text box or label that stores all of its own data.
  Adapted for use with L{View.Control.Text}.

  @ivar multiline: Are multiple lines supported?
  @type multiline: boolean
  @ivar chunks: All chunks of text
  @type chunks: list
  @ivar pos: Active chunk index
  @type pos: integer
  @ivar first_activate: Is this the first activation of this object?
  @type first_activate: boolean
  @ivar last_chunks: Chunks in the text before deactivation used to later detect
    text changes
  @type last_chunks: list of L{DynamicChunk}
  @ivar search_anchor: Position at the start of a search
  @type search_anchor: 2-tuple
  '''
  advise(instancesProvide=[IText, ISearchable, IInteractive])
  END_CHUNK_CHAR = 'new line'

  def __init__(self, context, path, multiline=True):
    '''
    Initializes an instance.

    See instance variables for parameter descriptions.
    '''
    super(TextBox, self).__init__(context, path)
    self.chunks = [self._NewChunk()]
    self.first_activate = True
    self.pos = 0
    self.multiline = multiline
    self.last_chunks = None
    self.search_anchor = None

  def _NewChunk(self, text=''):
    '''
    @param: Text of the chunk
    @type: string
    @return: New L{Chunk} or subclass
    @rtype: L{Chunk}
    '''
    return Chunk(text)

  def GetIndex(self):
    '''
    @return: Index of the virtual caret within all chunk characters
    @rtype: integer
    '''
    wgen = [str(c) for c in self.chunks[:self.pos]]
    return len(' '.join(wgen)) + self.Chunk.Index
  Index = property(GetIndex)

  def Deactivate(self):
    '''
    Stores the current text before losing activation so that indirect changes
    in the subject can be detected later.
    '''
    self.last_chunks = self.chunks

  def HasChanged(self):
    '''
    Checks if the text has changed since the last activation.

    @return: Have the control values changed?
    @rtype: boolean
    '''
    rv = super(TextBox, self).HasChanged()
    chunks = self.BuildChunks()
    if rv or chunks != self.last_chunks:
      self.chunks = chunks
      self.last_chunks = chunks
      return True
    else:
      return False

  def GetActiveChunk(self):
    '''
    @return: Active chunk object
    @rtype: L{Chunk}
    '''
    return self.chunks[self.pos]
  Chunk = property(GetActiveChunk)

  def BuildChunks(self):
    '''
    Constructs a new list of chunks by fetching the current text in the subject
    and splitting it accross new lines. Strips all line ending characters.

    @return: List of chunks for the subject text
    @rtype: list
    '''
    # get the text from the connection
    text = GetAOText(self.subject)
    # quit early if the text is blank
    if text is None or text in ('', '\r','\n', '\r\n'):
      return [self._NewChunk()]
    # break text into chunks by explicit lines
    chunks = []
    for line in text.split('\r'):
      c = self._NewChunk(line.strip('\n'))
      if not self.multiline and c.Size == 0:
        continue
      chunks.append(c)
    return chunks

  def UpdateChunks(self):
    '''
    Updates the held chunks by fetching the new chunks from the text control.
    '''
    self.pos = 0
    self.chunks = self.BuildChunks()

  def Activate(self):
    '''
    Updates held chunks from the text currently in the control.
    '''
    ready = super(TextBox, self).Activate()
    if ready and self.first_activate:
      # only update on first activate else caret pos is lost
      self.UpdateChunks()
      self.first_activate = False
    return ready

  def _GetChunkCount(self):
    '''
    @return: Number of stored chunks
    @rtype: integer
    '''
    return len(self.chunks)

  def GetWordCount(self, all=True):
    '''
    @param all: Get total word count (True), or words up to here (False)?
    @type all: boolean
    @return: Number of words in the text
    @rtype: integer
    '''
    if all:
      wgen = [str(c) for c in self.chunks]
      return len('\n'.join(wgen).split())
    else:
      wgen = [str(c) for c in self.chunks[:self.pos]]
      return len('\n'.join(wgen).split()) + \
             len(self.Chunk.GetFromBeginning().split())

  def GetAllText(self):
    '''
    @return: All stored text separated by new lines
    @rtype: string
    '''
    return '\n'.join([str(c) for c in self.chunks])

  def GetChunkText(self, which=IText.BOTH):
    '''
    Gets some or all of the text in the active chunk.

    @param which: Which portion of the chunk to get: all, from start, to end
    @type which: integer
    @return: Requested text
    @rtype: string
    '''
    if which == IText.BOTH:
      # get all text in the chunk
      return str(self.Chunk)
    elif which == IText.FROM_START:
      # get text in this chunk from the beginning to here
      return self.Chunk.GetFromBeginning()
    elif which == IText.TO_END:
      # get text in this chunk from here to the end
      return self.Chunk.GetToEnd()

  def GetWordText(self, which):
    '''
    Gets a nearby word.

    @param which: Which word to get: current, next, or previous
    @type which: integer
    @return: Requested text
    @rtype: string
    '''
    if which == IText.CURR:
      return self.Chunk.GetCurrentWord()
    elif which == IText.PREV:
      return self.Chunk.GetPrevWord()

  def GetCharText(self, which):
    '''
    Gets a nearby character.

    @param which: Which character to get: current, next, or previous
    @type which: integer
    @return: Requested text
    @rtype: string
    '''
    if which == IText.CURR:
      rv = self.Chunk.GetCurrentChar()
    elif which == IText.PREV:
      rv = self.Chunk.GetPrevChar()
    elif which == IText.NEXT :
      rv = self.Chunk.GetNextChar()
    return rv or self.END_CHUNK_CHAR

  def GetBounds(self):
    '''
    @return: If the caret is in the first or last chunk, start or end of the
        chunk
    @type: 4-tuple of boolean
    '''
    return (self.IsFirstChunk(), self.IsLastChunk(),
            self.Chunk.IsAtStart(), self.Chunk.IsAtEnd())

  def NextChunk(self, skip=False):
    '''
    Moves the caret to the start of the next chunk. The start can either be
    the very start of the chunk, or the first non-whitespace charater in the
    chunk.

    @param skip: Skip to the start of the first word (non-whitespace char)?
    @type skip: boolean
    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i = self.Chunk.MoveEnd()
    caret = CaretDelta(i, *self.GetBounds())

    if not self.IsLastChunk():
      # moved the caret to the next chunk if this one is not the last
      self.pos += 1
      caret.NewChunk = True
      caret.Moved += 1
      if skip:
        # skip to the first non-whitespace char
        caret.Moved += self.Chunk.MoveFirstWordFromStart()
    return caret

  def PrevChunk(self):
    '''
    Moves the caret to the start of this chunk if it is not already there.
    Otherwise, moves the caret to the start of the previous chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i, o = self.Chunk.MoveFirstWordFromCurrent()
    caret = CaretDelta(i, *self.GetBounds())
    if i == 0 and not self.IsFirstChunk():
      # moved to the previous chunk
      self.Chunk.MoveStart()
      self.pos -= 1
      caret.NewChunk = True
      j, tmp = self.Chunk.MoveFirstWordFromCurrent()
      caret.Moved = -i-o-j-1
    else:
      # moved to the start of this chunk or nowhere
      caret.Moved = -caret.Moved
    return caret

  def NextWord(self):
    '''
    Moves the caret to the start of the next word.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    this, i = self.Chunk.MoveNextWord()
    caret = CaretDelta(i, *self.GetBounds())
    if not this and not self.IsLastChunk():
      # moved one word in the next chunk
      caret = self.NextChunk(True)
      caret.Moved = i
    return caret

  def PrevWord(self):
    '''
    Moves the caret to the start of this word if it is not already there.
    Otherwise, moves it to the start of the previous word.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    # move back one word
    this, i = self.Chunk.MovePrevWord()
    caret = CaretDelta(i, *self.GetBounds())
    if not this and not self.IsFirstChunk():
      # moved into the previous chunk
      self.pos -= 1
      caret.NewChunk = True
      j = self.Chunk.MoveLastWordFromEnd()
      caret.Moved = i+j-1
    return caret

  def NextChar(self):
    '''
    Moves the caret to the next character.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i = self.Chunk.MoveNextChar()
    caret = CaretDelta(i, *self.GetBounds())
    if i == 0 and not self.IsLastChunk():
      # moved to the next chunk
      caret = self.NextChunk(False)
      caret.Moved -= 1
    return caret

  def PrevChar(self):
    '''
    Moves the caret to the previous character.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i = self.Chunk.MovePrevChar()
    caret = CaretDelta(i, *self.GetBounds())
    if i == 0 and not self.IsFirstChunk():
      # moved to the previous chunk
      self.pos -= 1
      caret.NewChunk = True
      caret.Moved -= 1
    return caret

  def MoveXChars(self, val):
    '''
    Moves the caret the given number of characters in the current chunk. A
    negative value indicates moving backward. Snaps to the bounds of the chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i = self.Chunk.MoveXChars(val)
    return CaretDelta(i, *self.GetBounds())
  
  def MoveStartChunk(self):
    '''
    Moves the caret to the start of the current chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    o = self.Chunk.MoveStart()
    return CaretDelta(o, *self.GetBounds())

  def MoveStart(self):
    '''
    Moves the caret to the start of the text box.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    o = 0
    for i in range(self.pos, -1, -1):
      o += self.chunks[i].MoveStart()
    self.pos = 0
    return CaretDelta(o, *self.GetBounds())
  
  def MoveEndChunk(self):
    '''
    Moves the caret to the end of the current chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    o = self.Chunk.MoveEnd()
    return CaretDelta(o, *self.GetBounds())

  def MoveEnd(self):
    '''
    Moves the caret to the end of the text box.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    o = 0
    for i in range(self.pos, self._GetChunkCount()):
      o += self.chunks[i].MoveEnd()
    self.pos = self._GetChunkCount()-1
    return CaretDelta(o, *self.GetBounds())

  def IsFirstChunk(self):
    '''
    Checks if the virtual caret is in the first chunk.

    @return: Is the first chunk active?
    @rtype: boolean
    '''
    return self.pos == 0

  def IsLastChunk(self):
    '''
    Checks if the virtual caret is in the last chunk.

    @return: Is the last chunk active?
    @rtype: boolean
    '''
    return self.pos == (self._GetChunkCount() - 1)

  def PeekChunkText(self):
    '''
    Gets all of the text from the next chunk if it exists.

    @return: All text in the next chunk or None if does not exist
    @rtype: string
    '''
    try:
      return str(self.chunks[self.pos+1])
    except IndexError:
      return None

  def _SearchAhead(self, text, current):
    '''
    Search for the next match of the given text in the textbox.

    @param text: Search target
    @type text: string
    @param current: Consider the current match too?
    @type current: boolean
    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    # search for the given text without updating the caret
    past = []
    for chunk in self.chunks[self.pos:]:
      i = chunk.FindNext(text, int(not current))
      past.append(i)
      if i is not None:
        break
    if past and past[-1] is None:
      # no match found, end of text
      return
    # update all chunk pointers up to the match
    moved = 0
    for chunk in self.chunks[self.pos:]:
      try:
        i = past.pop(0)
      except IndexError:
        break
      if i is None:
        moved += chunk.MoveEnd() + 1
        self.pos += 1
      else:
        moved += chunk.MoveXChars(i)
    return CaretDelta(moved, *self.GetBounds())

  def _SearchBehind(self, text, current):
    '''
    Search for the previous match of the given text in the textbox.

    @param text: Search target
    @type text: string
    @param current: Consider the current match too?
    @type current: boolean
    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    # search for the given text without updating the caret
    past = []
    for chunk in self.chunks[self.pos::-1]:
      i = chunk.FindPrev(text, 0)
      past.append(i)
      if i is not None:
        break
    if past and past[-1] is None:
      # no match found, end of text
      return
    # update all chunk pointers up to the match
    moved = 0
    for chunk in self.chunks[self.pos::-1]:
      try:
        i = past.pop(0)
      except IndexError:
        break
      if i is None:
        moved += chunk.MoveStart() - 1
        self.pos -= 1
      else:
        moved += chunk.MoveXChars(i)
    # return a caret object containing the number of characters traversed
    return CaretDelta(moved, *self.GetBounds())

  def SearchForNextMatch(self, text, current):
    '''
    Search for the next match of the given text in the textbox. Calls
    L{_SearchAhead} to perform the actual work since ISearchable requires this
    method to return a boolean while L{_SearchAhead} must return a L{CaretInfo}.

    @param text: Search target
    @type text: string
    @param current: Consider the current match too?
    @type current: boolean
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    caret = self._SearchAhead(text, current)
    if caret is None:
      return None
    else:
      return False

  def SearchForPrevMatch(self, text, current):
    '''
    Search for the previous match of the given text in the textbox. Calls
    L{_SearchBehind} to perform the actual work since ISearchable requires this
    method to return a boolean while L{_SearchBehi} must return a
    L{CaretInfo}.

    @param text: Search target
    @type text: string
    @param current: Consider the current match too?
    @type current: boolean
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    caret = self._SearchBehind(text, current)
    if caret is None:
      return None
    else:
      return False

  def SearchStart(self):
    '''
    Stores the current chunk index and the caret position within that chunk.
    '''
    self.search_anchor = (self.pos, self.Chunk.GetIndex())

  def SearchReset(self):
    '''
    Resets the caret position to the L{search_anchor}. Ensures all chunks are
    in the proper state.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    apos = self.search_anchor[0]
    aind = self.search_anchor[1]
    moved = 0
    if self.pos > apos:
      while self.pos > apos:
        # traverse backwards through the chunks to the anchor chunk
        moved += self.Chunk.MoveStart() - 1
        self.pos -= 1
      # move to the offset in the anchor chunk
      moved += self.Chunk.MoveXChars(aind - self.Chunk.GetSize())
    elif self.pos < apos:
      while self.pos < apos:
        # traverse forward through the chunks to the anchor chunk
        moved += self.Chunk.MoveEnd() + 1
        self.pos += 1
      # move to the offset in the anchor chunk
      moved += self.Chunk.MoveXChars(aind)
    else:
      index = self.Chunk.GetIndex()
      if index > aind:
        moved += self.Chunk.MoveXChars(aind - index)
      elif index < aind:
        moved += self.Chunk.MoveXChars(index - aind)
    # return a caret object containing the number of characters traversed
    return CaretDelta(moved, *self.GetBounds())

class EditableTextBox(TextBox):
  '''
  Editable text box that stores all of its own data. Adapted for use with
  L{View.Control.ReadText}.

  @todo: add flag for checking programmatic changes while editing?

  @ivar reset: Reset the caret to the beginning on activation?
  @type reset: boolean
  @ivar clear: Clear initial text on first activation?
  @type clear: boolean
  '''
  advise(instancesProvide=[IEditableText, IInteractive, IDeletable])

  def __init__(self, context, path, multiline=True, reset=False, clear=False):
    super(EditableTextBox, self).__init__(context, path, multiline)
    self.reset = reset
    self.clear = clear

  def _NewChunk(self, text=''):
    return DynamicChunk(text)

  def Activate(self):
    '''
    Activates the control by clearing the text and resetting the caret to the
    start if desired.
    '''
    ready = super(EditableTextBox, self).Activate()
    if ready:
      # give the textbox the input focus
      self.subject.Select(FOCUS)
      if self.clear:
        # clear text on first activation only
        self.Delete()
        self.clear = False
      if self.reset:
        # reset caret position on all activations
        for i in range(self.pos, -1, -1):
          self.chunks[i].MoveStart()
        self.pos = 0
        self.WarpOSCaret()
    return ready

  def MoveOSCaret(self, steps):
    '''
    Moves the OS caret to the left or right the given number of steps by
    synthesizing keystrokes.

    @param steps: Positive characters to the right, negative to the left.
    @type steps: number
    '''
    if steps is None:
      return
    elif steps > 0:
      self.subject.SendKeys('{RIGHT %d}' % steps)
    elif steps < 0:
      self.subject.SendKeys('{LEFT %d}' % (-1*steps))

  def WarpOSCaret(self, start=True):
    '''
    Warps the OS caret to the start or end of the text box.

    @param start: Warp to the start of the text (True) or the end (False)?
    @type start: boolean
    '''
    if start:
      self.subject.SendKeys('^{HOME}')
    else:
      self.subject.SendKeys('^{END}')

  def NextChunk(self, skip=False):
    caret = super(EditableTextBox, self).NextChunk(skip)
    self.MoveOSCaret(caret.Moved)
    return caret

  def PrevChunk(self):
    caret = super(EditableTextBox, self).PrevChunk()
    self.MoveOSCaret(caret.Moved)
    return caret

  def NextWord(self):
    caret = super(EditableTextBox, self).NextWord()
    self.MoveOSCaret(caret.Moved)
    return caret

  def PrevWord(self):
    caret = super(EditableTextBox, self).PrevWord()
    self.MoveOSCaret(caret.Moved)
    return caret

  def NextChar(self):
    caret = super(EditableTextBox, self).NextChar()
    self.MoveOSCaret(caret.Moved)
    return caret

  def PrevChar(self):
    caret = super(EditableTextBox, self).PrevChar()
    self.MoveOSCaret(caret.Moved)
    return caret

  def MoveXChars(self, val):
    caret = super(EditableTextBox, self).MoveXChars(val)
    self.MoveOSCaret(caret.Moved)
    return caret

  def MoveStart(self):
    caret = super(EditableTextBox, self).MoveStart()
    self.WarpOSCaret(True)
    return caret

  def MoveEnd(self):
    caret = super(EditableTextBox, self).MoveEnd()
    self.WarpOSCaret(False)
    return caret
  
  def MoveStartChunk(self):
    caret = super(EditableTextBox, self).MoveStartChunk()
    self.MoveOSCaret(caret.Moved)
    return caret

  def MoveEndChunk(self):
    caret = super(EditableTextBox, self).MoveEndChunk()
    self.MoveOSCaret(caret.Moved)
    return caret

  def SetText(self, text):
    '''
    Sets the text in the text control to the given value.

    @param text: Text to store
    @type text: string
    '''
    self.subject.SendKeys('^{HOME}+(^{END}){DEL}')
    self.subject.SendKeys(text)
    self.UpdateChunks()

  def Delete(self):
    '''Deletes all text.'''
    self.SetText('')

  def DeleteNext(self):
    '''
    Deletes character to the right of the cursor.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    caret = CaretDelta(0, *self.GetBounds())
    prev, curr = self.Chunk.PrevWord, self.Chunk.Word
    is_del, del_char = self.Chunk.Delete()
    if is_del:
      caret.Char = del_char
      if prev and curr and self.Chunk.Word == prev+curr:
        # words joined
        caret.Joined = True
        caret.NewWord = True
      elif caret.Char == ' ' and self.Chunk.Char != ' ':
        # touching a new word
        caret.NewWord = True
      self.subject.SendKeys('{DEL}')
    elif not self.IsLastChunk():
      # chunks joined
      caret.Char = self.END_CHUNK_CHAR
      self.Chunk.Join(self.chunks[self.pos+1])
      self.chunks.pop(self.pos+1)
      self.subject.SendKeys('{DEL}')
      caret.NewChunk = True
      caret.Joined = True
    return caret

  def DeletePrev(self):
    '''
    Deletes character to the left of the cursor.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    pos = self.GetBounds()
    prev, curr = self.Chunk.PrevWord, self.Chunk.Word
    is_del, del_char = self.Chunk.DeletePrev()
    caret = CaretDelta(int(is_del), *pos)
    if is_del:
      caret.Char = del_char
      if prev and curr and self.Chunk.Word == prev+curr:
        # words joined
        caret.Joined = True
        caret.NewWord = True
      elif caret.Char == ' ' and self.Chunk.PrevChar != ' ':
        # touching a new word
        caret.NewWord = True
      self.subject.SendKeys('{BACKSPACE}')
    elif not self.IsFirstChunk():
      # chunks joined
      self.pos -= 1
      self.Chunk.Join(self.chunks[self.pos+1])
      self.chunks.pop(self.pos+1)
      self.subject.SendKeys('{BACKSPACE}')
      caret.NewChunk = True
      caret.Joined = True
    return caret
  
  def InsertText(self, text):
    '''
    Insert a blob of text at the caret position.
    
    @param text: Text to insert
    @type text: string
    '''
    rv = map(self.InsertChar, text)
    return rv[-1]

  SPACE_CATS = ('C', 'Z', 'P')

  def InsertChar(self, char):
    '''
    Insert a new character at the caret position.

    @param char: Character to insert
    @type char: string
    '''
    prev, next = self.Chunk.Put(char)
    caret = CaretDelta(1, *self.GetBounds())
    caret.Char = char
    # determine unicode categories
    try:
      is_space = unicodedata.category(unicode(char))[0] in self.SPACE_CATS
    except TypeError, e:
      is_space = False
    try:
      prev_is_space = unicodedata.category(unicode(prev))[0] in self.SPACE_CATS
    except TypeError, e:
      prev_is_space = False
    try:
      next_is_space = unicodedata.category(unicode(next))[0] in self.SPACE_CATS
    except TypeError, e:
      next_is_space = False
    if prev and next and is_space and not prev_is_space and not next_is_space:
      # split in two
      caret.Split = True
    elif is_space and not prev_is_space:
      # new word
      caret.NewWord = True
    self.subject.SendKeys('{%s}' % char)
    return caret

  def InsertChunk(self):
    '''
    Insert a new line at the caret position.

    @param char: Character to insert
    @type char: string
    '''
    if not self.multiline: return None
    # create a new chunk
    nc = self.Chunk.Split()
    caret = CaretDelta(1, *self.GetBounds())
    caret.Char = '\n'
    if nc.Size == 0:
      # new chunk added
      caret.NewChunk = True
    self.pos += 1
    self.chunks.insert(self.pos, nc)
    if nc.Size != 0:
      # chunk split in two
      caret.Split = True
    self.subject.SendKeys('{ENTER}')
    return caret

  def SearchForNextMatch(self, text, current):
    caret = self._SearchAhead(text, current)
    if caret is None:
      return None
    else:
      self.MoveOSCaret(caret.Moved)
      return False

  def SearchForPrevMatch(self, text, current):
    caret = self._SearchBehind(text, current)
    if caret is None:
      return None
    else:
      self.MoveOSCaret(caret.Moved)
      return False

  def SearchReset(self):
    caret = super(EditableTextBox, self).SearchReset()
    self.MoveOSCaret(caret.Moved)
    return caret

class EditableDocument(EditableTextBox):
  def UpdateChunks(self):
    '''Do nothing.'''
    pass

class OverwritableTextBox(EditableTextBox):
  def UpdateChunks(self):
    '''Do not consider text already in the box.'''
    pass

class SimpleDocument(TextBox):
  '''
  Simple hypertext document that stores its data across a number of child nodes
  of varying roles. Entire document is loaded and cached as objects. Adapted
  for use with L{View.Control.Text}.

  @ivar children: Children stored to detect later changes
  @type children: list of pyAA.AccessibleObject
  '''
  END_CHUNK_CHAR = 'space'

  def __init__(self, context, path):
    '''
    Initializes an instance.

    See instance variables for parameter descriptions.
    '''
    super(SimpleDocument, self).__init__(context, path, multiline=True)
    self.children = []

  def Activate(self):
    '''
    Updates held chunks from the text currently in the control.
    '''
    ready = super(TextBox, self).Activate()
    if ready:
      # caret position is lost when we reactivate!!! working around bug in
      # stability
      self.UpdateChunks()
      self.first_activate = False
    return ready

  def HasChanged(self):
    '''
    Checks if the previously held children are now invalid. If they are,
    considers the document changed.

    @return: Is the previously held subject invalid?
    @rtype: boolean
    '''
#     # always assumed changed on first activation
#     if self.first_activate:
#       self.Activate()
#       return True
#     # check if the previously held children are alive or not
#     for c in self.children:
#       try:
#         c.Name
#       except pyAA.Error:
#         # reactivate and update chunks
#         if self.Activate():
#           self.UpdateChunks()
#         return True
#     # check if the current number of children equals the old number of children
#     if self.Activate():
#       if self.subject.ChildCount != len(self.children):
#         self.UpdateChunks()
#         return True
    if self.Activate(): # self.first_activate or
      self.UpdateChunks()
      return True
    return False

  def UpdateChunks(self):
    '''
    Grabs all the chunks of text immediately. Resets the chunk pointer to the
    beginning of the document.
    '''
    self.pos = 0
    self.children = self.subject.Children
    if len(self.children) == 0:
      self.chunks = [Chunk()]
    else:
      self.chunks = []
      for child in self.children:
        text = GetAOText(child).strip()
        if text: self.chunks.append(Chunk(text))
