'''
Defines Clique interfaces.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from protocols import Interface

class IOption(Interface):
  '''
  Allows an object to be listed by a L{Chooser} instance.
  '''
  def GetObject(): pass
  def GetName(): pass

class IContext(Interface):
  '''Allows access to child objects at a given path.'''
  def GetObjectAt(path): pass

class IInteractive(Interface):   
  '''
  Allows activation and deactivation of an object. Defines methods for getting
  an object's name and determining if an object has changed.
  '''
  def Activate(): pass
  def Deactivate(): pass
  def GetName(override, default): pass
  def HasChanged(): pass

class ISeekable(Interface):
  '''
  Allows seeking to an item in this object given a single character.
  '''
  BACKWARD, FORWARD = 0, 1
  def SeekToItem(pred, direction=FORWARD): pass
  
class ISearchable(Interface):
  '''
  Allows searching to an item in this object given a string. Supports 
  navigation to the next and previous matching item.
  '''
  def SearchStart(): pass
  def SearchForNextMatch(text, current): pass
  def SearchForPrevMatch(text, current): pass
  def SearchReset(): pass
  
class ISortable(Interface):
  '''
  Allows sorting of items based on one or more criteria.
  '''
  def GetSortName(): pass
  def SortNext(): pass
  def SortPrev(): pass
  
class ISelectable(Interface):
  '''
  Allows the selection of one or all items managed by an object.
  '''
  def Reselect(): pass
  def SelectAllItems(): pass
  def UnselectItems(): pass
  
class IDeletable(Interface):
  '''
  Allows the deletion of one item managed by an object.
  '''
  def Delete(): pass
  
class IDetailable(Interface):
  '''
  Allows access to additional information about the currently selected item 
  managed by an object.
  '''
  def GetFields(): pass
  def GetInheritedFields(): pass
  
class IStrideable(Interface):
  '''
  Allows variable levels of navigation through items.
  '''
  def NextLevel(): pass
  def PrevLevel(): pass
  def GetLevel(): pass
  
class IInfiniteCollection(Interface):
  '''
  Allows navigation through items via previous and next commands. Allows access
  to the currently selected item and its name.
  '''
  def GetSelectedName(default=''): pass
  def NextItem(): pass
  def PrevItem(): pass
    
class IFiniteCollection(IInfiniteCollection):
  '''
  Allows navigation to the first item in a bounded collection. Provides methods
  for getting the total number of items and the currently selected item's index.
  '''
  def GetItemCount(): pass
  def GetIndex(): pass
  def FirstItem(): pass
  
class IList(IFiniteCollection):
  '''
  Allows navigation to the last item in a bounded collection.
  '''
  def LastItem(): pass
    
class ITree(IFiniteCollection):
  '''
  Allows access to information about items managed at higher and lower levels.
  '''
  def GetParentName(default=''): pass  
  def GetChildCount(): pass
  def HasChildren(): pass
  def HasParent(): pass
  
class ILabel(Interface):
  '''
  Allows read-only access to an entire body of text that can only be retrieved
  as one large string.
  '''
  def __str__(self): pass
  def GetAllText(): pass
    
class IText(Interface):
  '''
  Allows read-only access to properties of a body of text and navigation by
  character, word, and chunk.
  '''
  BOTH, FROM_START, TO_END = 0, 1, 2
  CURR, PREV, NEXT = 0, 2, 4
  def GetAllText(): pass
  def GetWordCount(all=True): pass
  def GetChunkText(which): pass
  def GetWordText(which): pass
  def GetCharText(which): pass
  def NextChunk(skip=False): pass
  def PrevChunk(): pass
  def NextWord(): pass
  def PrevWord(): pass
  def PrevChar(): pass
  def NextChar(): pass
  def IsLastChunk(): pass
  def IsFirstChunk(): pass
  def MoveXChars(diff): pass
  def MoveStart(self): pass
  def MoveEnd(self): pass
  def MoveStartChunk(self): pass
  def MoveEndChunk(self): pass

class IHypertext(IDetailable,IText):
  '''
  Allows read-only access to extended properties and actions of rich text.
  '''
  def IsLink(): pass
  def FollowLink(): pass
  def GetTitle(): pass
  
class IEditableText(IText):
  '''
  Allows write access to a body of text with methods to replace all text, insert
  a character, delete a character, and insert a new chunk.
  '''
  def SetText(): pass
  def DeleteNext(): pass
  def DeletePrev(): pass
  def InsertChar(char): pass
  def InsertText(text): pass
  def InsertChunk(): pass
  
class ISound(Interface):
  '''
  Provides a mapping from an object state, action, warn, and identity to a sound
  representing it.
  '''
  def State(name): pass
  def Action(name): pass
  def Warn(name): pass
  def Identity(name=''): pass
