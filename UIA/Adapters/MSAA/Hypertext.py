'''
Defines adapters for text types like labels, text boxes, and hypertext.

@todo let document detect when subject is dead, update pointer to start

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
from Text import CaretDelta, Chunk
# clipboard functions for getting all text
import win32clipboard as clip
import win32con

class HypertextDocument(Adapter):
  '''
  Complex hypertext document that stores its data across a number of child nodes
  of varying roles. Document is walked as is, and not pulled entirely into the
  client first. Adapted for use with L{View.Control.Text}.

  @ivar pointer: Current location within the document
  @type pointer: Accessible
  @ivar chunk: Current chunk of text
  @type chunk: L{Text.Chunk}
  @ivar first_activate: Will the next call to L{Activate} be the first?
  @type first_activate: boolean
  @ivar search_anchor: Position at the start of a search
  @type search_anchor: Accessible
  '''
  advise(instancesProvide=[IHypertext, IInteractive, ISeekable, ISearchable])
  END_CHUNK_CHAR = 'break'

  def __init__(self, context, path):
    '''
    Initializes an instance.

    See instance variables for parameter descriptions.
    '''
    super(HypertextDocument, self).__init__(context, path)
    self.pointer = None
    self.chunk = Chunk()
    self.first_activate = True

  def Activate(self):
    # only set the pointer to the start of the doc on first activate
    rv = super(HypertextDocument, self).Activate()
    if rv:
      if self.first_activate or self.pointer is None:
        # first time, build pointer
        self._MovePointer(self.subject)
        self.first_activate = False
    return rv

  def HasChanged(self):
    '''Make sure pointer is refreshed on next activate.'''
    self.pointer = None

  def GetTitle(self):
    '''
    @return: Title of the document
    @rtype: string
    '''
    return self.subject.Name

  def IsLink(self):
    '''
    @return: Is the pointer resting on a hyperlink?
    @rtype: boolean
    '''
    return self.pointer.Role == pyAA.Constants.ROLE_SYSTEM_LINK

  def FollowLink(self):
    '''
    Activates the link at the pointer.
    '''
    return self.pointer.DoDefaultAction()

  def GetFields(self):
    '''
    Gets role, state, and description strings from the current chunk. Also
    returns a flag indicating whether the information is trivial, namely 
    the current pointer rests on regular document text.

    @return: Fields keyed by role, state, and description
    @rtype: dictionary
    '''
    rt = self.pointer.RoleText
    st = self.pointer.StateText
    # compute whether field information is trivial
    triv = (rt == 'editable text' and st.find('read only') > -1)
    return dict(role=rt,
                state=st,
                description=self.pointer.Description,
                trivial=triv)

  def GetInheritedFields(self):
    '''
    Gets role, state, and description strings from the current chunk and all
    ancestors of the chunk. Also returns a flag indicating whether the
    information is trivial, namely the current pointer rests on regular
    document text.

    @return: List of fields keyed by role, state, and description
    @rtype: list of dict
    '''
    orig = self.pointer
    result = []

    # always store current chunk info
    fields = self.GetFields()
    result.append(fields)

    while fields['role'] != 'document':
      # stop after storing info about the document
      try:
        self.pointer = self.pointer.Parent
      except Exception:
        break
      fields = self.GetFields()
      result.append(fields)
    self.pointer = orig
    # start at top level
    result.reverse()
    return result
    
  def GetAllText(self): 
    # select all text
    self.subject.SendKeys('^{a}')
    # copy text
    self.subject.SendKeys('^{c}')
    # get text from the clipboard
    w.OpenClipboard() 
    text = w.GetClipboardData(win32con.CF_TEXT) 
    w.CloseClipboard()
    return text

  def GetWordCount(self, all=True):
    if all:
      # get all text
      text = self.GetAllText()
      # count words
      return len(text.split())
    else:
      # TODO: hard to get words up to here
      return 0

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
      return str(self.chunk)
    elif which == IText.FROM_START:
      # get text in this chunk from the beginning to here
      return self.chunk.GetFromBeginning()
    elif which == IText.TO_END:
      # get text in this chunk from here to the end
      return self.chunk.GetToEnd()

  def GetWordText(self, which):
    '''
    Gets a nearby word.

    @param which: Which word to get: current, next, or previous
    @type which: integer
    @return: Requested text
    @rtype: string
    '''
    if which == IText.CURR:
      return self.chunk.GetCurrentWord()
    elif which == IText.PREV:
      return self.chunk.GetPrevWord()

  def GetCharText(self, which):
    '''
    Gets a nearby character.

    @param which: Which character to get: current, next, or previous
    @type which: integer
    @return: Requested text
    @rtype: string
    '''
    rv = ''
    if which == IText.CURR:
      rv = self.chunk.GetCurrentChar()
    elif which == IText.PREV:
      rv = self.chunk.GetPrevChar()
    elif which == IText.NEXT :
      rv = self.chunk.GetNextChar()
    return rv or self.END_CHUNK_CHAR

  def NextWord(self):
    '''
    Moves the caret to the start of the next word.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    this, i = self.chunk.MoveNextWord()
    caret = CaretDelta(i, *self._GetBounds())
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
    this, i = self.chunk.MovePrevWord()
    caret = CaretDelta(i, *self._GetBounds())
    if not this and not self.IsFirstChunk():
      # moved into the previous chunk
      self._MovePointer(self._NavPrev(self.pointer))
      caret.NewChunk = True
      j = self.chunk.MoveLastWordFromEnd()
      caret.Moved = i+j-1
    return caret

  def NextChar(self):
    '''
    Moves the caret to the next character.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i = self.chunk.MoveNextChar()
    caret = CaretDelta(i, *self._GetBounds())
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
    i = self.chunk.MovePrevChar()
    caret = CaretDelta(i, *self._GetBounds())
    if i == 0 and not self.IsFirstChunk():
      # move to the start of the previous chunk
      self.PrevChunk()
      self.chunk.MoveEnd()
      caret.NewChunk = True
      caret.Moved -= 1
    return caret

  def NextChunk(self, skip=False):
    '''
    Moves the caret to the start of the next chunk. The start can either be
    the very start of the chunk, or the first non-whitespace character in the
    chunk.

    @param skip: Skip to the start of the first word (non-whitespace char)?
    @type skip: boolean
    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i = self.chunk.MoveEnd()
    caret = CaretDelta(i, *self._GetBounds())
    if not self.IsLastChunk():
      # moved the caret to the next chunk if this one is not the last
      self._MovePointer(self._NavNext(self.pointer))
      caret.NewChunk = True
      caret.Moved += 1
      if skip:
        # skip to the first non-whitespace char
        caret.Moved += self.chunk.MoveFirstWordFromStart()
    return caret

  def PrevChunk(self):
    '''
    Moves the caret to the start of this chunk if it is not already there.
    Otherwise, moves the caret to the start of the previous chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i, o = self.chunk.MoveFirstWordFromCurrent()
    caret = CaretDelta(i, *self._GetBounds())
    if i == 0 and not self.IsFirstChunk():
      # moved to the previous chunk
      self._MovePointer(self._NavPrev(self.pointer))
      caret.NewChunk = True
      j, tmp = self.chunk.MoveFirstWordFromCurrent()
      caret.Moved = -i-o-j-1
    else:
      # moved to the start of this chunk or nowhere
      caret.Moved = -caret.Moved
    return caret

  def IsLastChunk(self): 
    '''
    Tries to navigate ahead to see if this is the last chunk or not.

    @return: In the last chunk?
    @rtype: boolean
    '''
    try:
      self._NavNext(self.pointer)
      return False
    except ReferenceError:
      return True

  def IsFirstChunk(self): 
    '''
    Compares paths to see if the pointer is at the root of the document.

    @return: In the first chunk?
    @rtype: boolean
    '''
    return self.pointer.Role == pyAA.Constants.ROLE_SYSTEM_DOCUMENT

  def MoveXChars(self, val):
    '''
    Moves the caret the given number of characters in the current chunk. A
    negative value indicates moving backward. Snaps to the bounds of the chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    i = self.chunk.MoveXChars(val)
    return CaretDelta(i, *self._GetBounds())
  
  def MoveStartChunk(self):
    '''
    Moves the caret to the start of the current chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    o = self.chunk.MoveStart()
    return CaretDelta(o, *self._GetBounds())

  def MoveStart(self):
    '''
    Moves the caret to the start of the document.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    self._MovePointer(self.subject)
    return CaretDelta(o, *self._GetBounds())
  
  def MoveEndChunk(self):
    '''
    Moves the caret to the end of the current chunk.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    o = self.chunk.MoveEnd()
    return CaretDelta(o, *self._GetBounds())

  def MoveEnd(self):
    '''
    Moves the caret to the end of the document.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    pointer = self.subject
    while 1:
      try:
        # fetch last child
        pointer = pointer.Navigate(pyAA.Constants.NAVDIR_LASTCHILD)
      except pyAA.Error:
        break
    # update our pointer and return caret information
    self._MovePointer(pointer)
    return CaretDelta(0, *self._GetBounds())

  def _MovePointer(self, pointer):
    '''
    Sets the pointer to a new location, and creates a corresponding chunk for
    its content.

    @param pointer: Pointer to an accessible
    @type pointer: Accessible
    '''
    self.pointer = pointer
    self.chunk = Chunk(self.pointer.Name)

  def _GetBounds(self):
    '''
    @return: If the caret is in the first or last chunk, start or end of the
        chunk
    @type: 4-tuple of boolean
    '''
    return (self.IsFirstChunk(), self.IsLastChunk(),
            self.chunk.IsAtStart(), self.chunk.IsAtEnd())

  def _NavPrev(self, pointer):
    '''
    Navigate to the previous element in the document starting at the given
    pointer.
    
    @param pointer: Acessible object reference
    @type pointer: Accessible
    @return: New pointer position
    @rtype: Accessible
    @raise RrferenceError: When there is no previous node
    '''
    if pointer.Role == pyAA.Constants.ROLE_SYSTEM_DOCUMENT:
      # don't navigate before start of document
      raise ReferenceError

    if not pointer.Name:
      # don't treat nodes that have content as having further children
      try:
        # try to get the last child of this node
        return pointer.Navigate(pyAA.Constants.NAVDIR_LASTCHILD)
      except pyAA.Error:
        pass

    try:
      # try to get the previous peer of this node
      return pointer.Navigate(pyAA.Constants.NAVDIR_PREVIOUS)
    except pyAA.Error:
      pass

    try:
      parent = pointer.Parent
    except pyAA.Error:
      raise ReferenceError

    while parent.Role != pyAA.Constants.ROLE_SYSTEM_DOCUMENT:
      # try to get the prvious peer of the parent node
      try:
        return parent.Navigate(pyAA.Constants.NAVDIR_PREVIOUS)
      except pyAA.Error:
        pass
      try:
        # move one level up
        parent = parent.Parent
      except pyAA.Error:
        raise ReferenceError
    # first node is the document itself
    return parent

  def _NavNext(self, pointer):
    '''
    Navigate to the next element in the document starting at the given
    pointer.
    
    @param pointer: Acessible object reference
    @type pointer: Accessible
    @return: New pointer position
    @rtype: Accessible
    '''
    if not pointer.Name or pointer.Role == pyAA.Constants.ROLE_SYSTEM_DOCUMENT:
      # try to get the first child of this node
      try:
        return pointer.Navigate(pyAA.Constants.NAVDIR_FIRSTCHILD)
      except pyAA.Error:
        pass
    # try to get the next peer of this node
    try:
      return pointer.Navigate(pyAA.Constants.NAVDIR_NEXT)
    except pyAA.Error:
      pass

    try:
      parent = pointer.Parent
    except pyAA.Error:
      raise ReferenceError

    while parent.Role != pyAA.Constants.ROLE_SYSTEM_DOCUMENT:
      # try to get the next peer of the parent node
      try:
        return parent.Navigate(pyAA.Constants.NAVDIR_NEXT)
      except pyAA.Error:
        pass
      try:
        # move one level up
        parent = parent.Parent
      except pyAA.Error:
        raise ReferenceError
    raise ReferenceError

  def SeekToItem(self, pred, direction=ISeekable.FORWARD):
    '''
    Seeks to an item matching the given predicate in the direction specified.

    @param pred: Function evaluate on each node to see if it is a match
    @type pred: callable
    @param direction: Forward or backward
    @type direction: integer
    @return: True if found and wrapped, False if found but not wrapped, None if
      no match
    @rtype: boolean
    '''
    pointer = self.pointer
    if direction == ISeekable.FORWARD:
      nav = self._NavNext
    else:
      nav = self._NavPrev

    while 1:
      try:
        pointer = nav(pointer)
      except ReferenceError:
        return None
      try:
        # test predicate
        rv = pred(pointer.RoleText, pointer.StateText)
      except Exception, e:
        pass
      else:
        if rv: 
          # a match, but not wrapped
          self._MovePointer(pointer)
          return False
    # no match
    return None

  def SearchStart(self):
    '''Stores the current pointer in case of a reset.'''
    self.search_anchor = self.pointer

  def SearchReset(self): 
    '''
    Resets the pointer to its initial location at the start of the search.

    @return: Info about the new caret state
    @rtype: L{CaretDelta}
    '''
    self._MovePointer(self.search_anchor)
    # number of chars moved is unknown
    return CaretDelta(0, *self._GetBounds())

  def SearchForNextMatch(self, text, current):
    '''
    @param text: Search target
    @type text: string
    @param current: Consider the current match too?
    @type current: boolean
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    # check current chunk for a hit, possibly within the current match
    # offset by one (not current) guarantees no hit within the same match
    i = self.chunk.FindNext(text, int(not current))
    if i is not None:
      # move caret to new location
      self.chunk.MoveXChars(i)
      # found, but no wrap
      return False

    # store current pointer
    pointer = self.pointer

    # search through all following chunks until end of doc
    while 1:
      try:
        pointer = self._NavNext(pointer)
      except ReferenceError:
        # not found
        break
      # check the new chunk
      i = Chunk(pointer.Name).FindNext(text, 0)
      if i is not None:
        # found a match, move there
        self._MovePointer(pointer)
        # move caret within the chunk
        self.chunk.MoveXChars(i)
        # found, but no wrap
        return False
    return None

  def SearchForPrevMatch(self, text, current):
    '''
    @param text: Search target
    @type text: string
    @param current: Consider the current match too?
    @type current: boolean
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    # check current chunk for a hit, possibly within the current match
    # offset by one (not current) guarantees no hit within the same match
    i = self.chunk.FindPrev(text, 0)
    if i is not None:
      # move caret to new location
      self.chunk.MoveXChars(i)
      # found, but no wrap
      return False

    # store current pointer
    pointer = self.pointer

    # search through all following chunks until end of doc
    while 1:
      try:
        pointer = self._NavPrev(pointer)
      except ReferenceError:
        # not found
        break
      # check the new chunk
      c = Chunk(pointer.Name)
      c.MoveEnd()
      i = c.FindPrev(text, 0)
      if i is not None:
        # found a match, move there
        self.pointer = pointer
        self.chunk = c
        # move caret within the chunk
        self.chunk.MoveXChars(i)
        # found, but no wrap
        return False
    return None
