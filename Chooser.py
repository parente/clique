'''
Defines a list model for choosing an object from a system menu.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from protocols import advise
from Interface import *
   
class Chooser(object):
  '''
  System menu. Provides IList, IInteractive, ISearchable, and ISeekable.
  
  @ivar options: Iterable of objects adapted to the L{IOption} interface
  @type options: iterable of L{IOption}s
  @ivar curr: Current item index 
  @type curr: index
  @ivar search_anchor: Default start of a full text search
  @type search_anchor: integer
  '''
  advise(instancesProvide=[IList, IInteractive, ISeekable, ISearchable])
  
  def __init__(self, options):
    '''
    Initializes the chooser by adapting the options to the L{IOption} interface.
    
    @param options: List of objects adaptable to L{IOption}
    @type options: list
    '''
    self.options = [IOption(opt) for opt in options]
    self.curr = 0
    self.search_anchor = 0

  def Activate(self):
    '''
    Always ready after instantiation.
    
    @return: Is this IInteractive ready?
    @rtype: boolean
    '''    
    return True
    
  def Deactivate(self):
    '''Do nothing.'''
    pass
  
  def GetName(self, override, default):
    '''
    Gets the name of the L{View} as the name for this model.
    
    @param override: Name specified by the L{View}
    @type override: string
    @param default: Default name for the L{View}
    @type default: string
    @return: Override or default name depending on what's available
    @rtype: string
    '''
    return override or default
    
  def GetSelectedName(self, default=''):
    '''
    @return: Name of the selected item
    @rtype: string
    '''
    try:
      return self.options[self.curr].GetName()
    except IndexError:
      return default
    
  def GetSelectedItem(self):
    '''
    @return: Selected item object
    @rtype: object
    '''
    try:
      return self.options[self.curr]
    except IndexError:
      return None
   
  def GetItemCount(self):
    '''
    @return: Number of items in the menu
    @rtype: integer
    '''
    return len(self.options)
    
  def GetIndex(self):
    '''
    @return: Index of the current item
    @rtype: integer
    '''
    return self.curr
    
  def FirstItem(self):
    '''Sets the selection to the first item.'''
    self.curr = 0
      
  def LastItem(self):
    '''Sets the selection to the last item.'''
    self.curr = self.GetItemCount()-1
      
  def PrevItem(self):
    '''
    Navigates to the previous item.
    
    @return: Did navigation wrap?
    @rtype: boolean
    '''
    count = len(self.options)
    if count == 0:
      return False
    c = self.curr - 1
    self.curr = c % count
    if c < 0:
      return True
    else:
      return False
    
  def NextItem(self): 
    '''
    Navigates to the next item.
    
    @return: Did navigation wrap?
    @rtype: boolean
    '''
    count = len(self.options)
    if count == 0:
      return False
    c = self.curr + 1
    self.curr = c % count
    if c >= count:
      return True
    else:
      return False
  
  def SeekToItem(self, char):
    '''
    Navigates to the next item with the given start letter.
    
    @return: Did navigation wrap? None if not found
    @rtype: boolean or None
    '''
    # seek forward
    for i in range(self.curr+1, len(self.options)):
      if self.options[i].GetName().lower()[0] == char.lower():
        self.curr = i
        return False
    # seek from the beginning
    for i in range(0, self.curr+1):
      if self.options[i].GetName().lower()[0] == char.lower():
        self.curr = i
        return True
    # the sought item does not exist
    return None
  
  def SearchStart(self):
    '''
    Indicates the start of a search so that the search anchor can be set.
    '''
    self.search_anchor = self.curr
  
  def SearchForNextMatch(self, text, current):
    '''
    Navigates to the next item containing the given text string.
    
    @param text: String of interest
    @type text: string
    @param current: Include current item in the search?
    @type current: boolean
    @return: Did navigation wrap? None if not found
    @rtype: boolean or None
    '''
    offset = int(not current)
    # search forward
    for i in xrange(self.curr+offset, len(self.options)):
      if self.options[i].GetName().lower().find(text) > -1:
        self.curr = i
        return False
    # search from the beginning
    for i in xrange(0, self.curr+offset):
      if self.options[i].GetName().lower().find(text) > -1:
        self.curr = i
        return True
    # no match to the current text
    return None
  
  def SearchForPrevMatch(self, text, current):
    '''
    Navigates to the previous item containing the given text string.
    
    @param text: String of interest
    @type text: string
    @param current: Include current item in the search?
    @type current: boolean
    @return: Did navigation wrap? None if not found
    @rtype: boolean or None
    '''
    offset = int(not current)
    # search backward
    for i in xrange(self.curr-offset, -1, -1):
      if self.options[i].GetName().lower().find(text) > -1:
        self.curr = i
        return False
    # search from the end
    for i in xrange(self.GetItemCount()-1, self.curr-offset, -1):
      if self.options[i].GetName().lower().find(text) > -1:
        self.curr = i
        return True
    # no match to the current text
    return None
  
  def SearchReset(self):
    '''
    Resets the current item to the one that was selected when the search began.
    '''
    self.curr = self.search_anchor
