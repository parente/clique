'''
Defines adapters for collection types like lists, trees, comboboxes, check
boxes, and radio buttons.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import re, time, pyAA
import Mixin
from Interface import *
from protocols import advise
from Constants import *
from Base import Adapter

class Collection(Adapter, Mixin.CircularSearchMixin):
  '''
  Virtual class. Implements code shared across L{Interfaces.ICollection} adapter
  derivatives.

  @ivar select_hack: Should selections be followed by another action 
      for broken collection control implementations?
  @type select_hack: boolean
  @ivar hack_type: Use 'left' click for hack or 'default' action
  @type hack_type: string
  @ivar search_anchor: Default start of a full text search
  @type search_anchor: integer
  '''
  def __init__(self, context, path, select_hack=False, hack_type='left'):
    '''
    Initializes last state variables and stores the select hack flag.
    '''
    super(Collection, self).__init__(context, path)
    self.last_selected = None
    self.last_count = None
    self.select_hack = select_hack
    self.hack_type = 'left'
    self.search_anchor = None

  def Activate(self):
    '''
    Selects the first item in the collection if a selection doesn't already
    exist.

    @return: Did the model activate properly?
    @rtype: boolean
    '''
    rv = Adapter.Activate(self)
    if rv and self.GetSelectedItem() is None:
      self.subject.SetFocus()
      # create a selection if there isn't one
      self.FirstItem()
    elif rv:
      # reselect the item with focus
      try:
        self.SetSelectedItem(self.GetSelectedItem())
      except (AttributeError, pyAA.Error):
        pass
    return rv

  def Deactivate(self):
    '''
    Stores the selected name and number of items before losing activation so
    that indirect changes in the collection can be detected later.
    '''
    try:
      self.last_count = self.GetItemCount()
    except AttributeError:
      return
    self.last_selected = self.GetSelectedName()

  def HasChanged(self):
    '''
    Checks if the selected item name or item count has changed since the control
    was last activated and in use.

    @return: Have the control values changed?
    @rtype: boolean
    '''
    rv = super(Collection, self).HasChanged()
    if not rv:
      return False
    selected = self.GetSelectedName()
    count = self.GetItemCount()
    if self.last_selected != selected or self.last_count != count:
      self.last_selected = selected
      self.last_count = count
      return True
    else:
      return False

  def GetItemCount(self):
    '''
    Virtual method. Always returns one as the item count.

    @return: Always 1
    @rtype: integer
    '''
    return 1

  def GetSelectedName(self, default=''):
    '''
    Gets the name of the selected focused item in the collection.

    @param default: Default name to return when collection empty
    @type default: string
    @return: Value of the name property
    @rtype: string or None
    '''
    try:
      return self.GetSelectedItem().Name
    except AttributeError:
      return default

  def GetSelectedItem(self):
    '''
    @return: Item that has the focus
    @rtype: pyAA.AccessibleObject or None
    '''
    try:
      return self.subject.Selection[0]
    except (IndexError):
      # select the first item in case we lost selection somewhere
      if self.FirstItem():
        try:
          return self.subject.Selection[0]
        except (pyAA.Error, AttributeError, IndexError):
          pass
    except (pyAA.Error, AttributeError):
      pass
    return None

  def SetSelectedItem(self, item):
    '''
    Shortcut for setting the selected item. Checks the select hack flag to see
    if the item should be clicked after selection in case the server side
    implementation is poor and is expecting a real mouse event.

    @param item: Item to select
    @type item: pyAA.AccessibleObject
    '''
    item.Select(SELECT_AND_FOCUS)
    if self.select_hack:
      if self.hack_type == 'left':
        item.LeftClick()
      elif self.hack_type == 'default':
        item.DoDefaultAction()

  def FirstItem(self):
    '''
    Selects the first item in the list.

    @return: Was the first item selected?
    @rtype: boolean
    '''
    try:
      c = self.subject.Navigate(FIRST)
    except pyAA.Error:
      return False
    self.SetSelectedItem(c)
    return True

  def _SearchStart(self):
    '''
    Callback for L{CircularSearch}. Gets the currently selected item.

    @return: Currently selected item
    @rtype: pyAA.Accessible
    '''
    return self.GetSelectedItem()

  def _SearchEnd(self):
    '''
    Callback for L{CircularSearch}. Does nothing.
    '''
    pass

  def _SearchAhead(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the next item to test.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    @return: Next item to test
    @rtype: pyAA.Accessible
    @raise ValueError: When the next item does not exist
    '''
    raise ValueError

  def _SearchBehind(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the previous item to test.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    @return: Previous item to test
    @rtype: pyAA.Accessible
    @raise ValueError: When the previous item does not exist
    '''
    raise ValueError

  def _SearchFirst(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the first item.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    @return: Next item to test
    @rtype: pyAA.Accessible
    @raise ValueError: When the first item does not exist
    '''
    raise ValueError

  def _SearchLast(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the last item.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    @return: Next item to test
    @rtype: pyAA.Accessible
    @raise ValueError: When the last item does not exist
    '''
    raise ValueError

  def _SearchSelectAhead(self, curr):
    '''
    Callback for L{CircularSearch}. Selects the current item when searching
    ahead.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    '''
    self.SetSelectedItem(curr)

  def _SearchSelectBehind(self, curr):
    '''
    Callback for L{CircularSearch}. Selects the current item when searching
    behind.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    '''
    self.SetSelectedItem(curr)

  def _SearchTestStartsWith(self, curr, text):
    '''
    Callback for L{CircularSearch}. Checks if the current item starts with the
    given text.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    @param text: Search string
    @type text: string
    @return: The current item starts with the given text?
    @rtype: boolean
    '''
    return curr.Name.lower().startswith(text.lower())

  def _SearchTestAll(self, curr, text):
    '''
    Callback for L{CircularSearch}. Checks if the current item contains all of
    the given text.

    @param curr: Current item to test
    @type curr: pyAA.AccessibleObject
    @param text: Search string
    @type text: string
    @return: The current item contains the given text?
    @rtype: boolean
    '''
    return curr.Name.lower().find(text.lower()) > -1

  def SeekToItem(self, char):
    '''
    Selects the next item beginning with the given character, if possible.

    @param char: Character of interest
    @type char: string
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    return self.CircularSearch(self._SearchStart, self._SearchEnd,
                               self._SearchAhead, self._SearchTestStartsWith,
                               self._SearchSelectAhead, self._SearchFirst, char,
                               False)

  def SearchForNextMatch(self, text, current):
    '''
    Selects the next item containing the search string, if possible.

    @param text: String of interest
    @type text: string
    @param current: Include current item in the search?
    @type current: boolean
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    return self.CircularSearch(self._SearchStart, self._SearchEnd,
                               self._SearchAhead, self._SearchTestAll,
                               self._SearchSelectAhead, self._SearchFirst, text,
                               current)

  def SearchForPrevMatch(self, text, current):
    '''
    Selects the previous item containing the search string, if possible.

    @param text: String of interest
    @type text: string
    @param current: Include current item in the search?
    @type current: boolean
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    return self.CircularSearch(self._SearchStart, self._SearchEnd,
                               self._SearchBehind, self._SearchTestAll,
                               self._SearchSelectBehind, self._SearchLast, text,
                               current)

  def SearchStart(self):
    '''
    Stores the item which was selected when search started.
    '''
    self.search_anchor = self.GetSelectedItem()

  def SearchReset(self):
    '''
    Resets the current item to the one that was selected when the search began.
    '''
    self.SetSelectedItem(self.search_anchor)

class List(Collection):
  '''
  Simple list box of items. Adapted for use with L{View.Control.List}.
  '''
  advise(instancesProvide=[IList, ISeekable, ISearchable, IInteractive,
                           ISelectable])

  def GetItemCount(self):
    '''
    @return: Number of child items in the collection
    @rtype: number
    '''
    # get the first item
    try:
      first = self.subject.Navigate(FIRST)
    except pyAA.Error:
      return 0
    # get the last item
    try:
      last = self.subject.Navigate(LAST)
    except pyAA.Error:
      return 0
    return last.ChildID-first.ChildID+1

  def GetIndex(self):
    '''
    @return: Index of the focused item
    @rtype: integer
    '''
    # get the first item
    try:
      first = self.subject.Navigate(FIRST)
    except pyAA.Error:
      return 0
    # compute the offset
    return self.GetSelectedItem().ChildID - first.ChildID

  def SelectAll(self):
    '''Selects all items.'''
    try:
      first = self.subject.Navigate(FIRST)
      last = self.subject.Navigate(LAST)
    except pyAA.Error:
      return
    first.Select(EXTEND_SELECT)
    last.Select(EXTEND_SELECT)

  def SelectNone(self):
    '''Deselects all items in the list.'''
    self.Focus.Select(SELECT_AND_FOCUS)
    self.Focus.Select(UIA.Constants.SELFLAG_REMOVESELECTION)

  def LastItem(self):
    '''
    Selects the last item in the list.

    @return: Was the last item selected?
    @rtype: boolean
    '''
    try:
      c = self.subject.Navigate(LAST)
    except pyAA.Error:
      return False
    self.SetSelectedItem(c)
    return True

  def NextItem(self):
    '''
    Selects the next item in the list or wraps to the first.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    try:
      n = self.GetSelectedItem().Navigate(NEXT)
      res = False
    except AttributeError:
      return False
    except pyAA.Error:
      n = self.subject.Navigate(FIRST)
      res = True
    self.SetSelectedItem(n)
    return res

  def PrevItem(self):
    '''
    Selects the previous item in the list or wraps to the last.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    try:
      n = self.GetSelectedItem().Navigate(PREVIOUS)
      res = False
    except AttributeError:
      return False
    except pyAA.Error:
      n = self.subject.Navigate(LAST)
      res = True
    self.SetSelectedItem(n)
    return res

  def _SearchAhead(self, curr):
    try:
      return curr.Navigate(NEXT)
    except pyAA.Error:
      raise ValueError

  def _SearchBehind(self, curr):
    try:
      return curr.Navigate(PREVIOUS)
    except pyAA.Error:
      raise ValueError

  def _SearchFirst(self, curr):
    try:
      # seek from the start
      return self.subject.Navigate(FIRST)
    except pyAA.Error:
      # there is no start, the list is empty
      raise ValueError

  def _SearchLast(self, curr):
    try:
      # seek from the end
      return self.subject.Navigate(LAST)
    except pyAA.Error:
      # there is no end, the list is empty
      raise ValueError

class EditableList(List):
  '''
  Simple list with support for deletion of items. Adapted for use with
  L{View.Control.List}.
  '''
  advise(instancesProvide=[IList, ISeekable, ISearchable, IInteractive,
                           IDeletable])

  def Delete(self):
    '''
    Removes the selected item from the list.
    '''
    self.subject.SendKeys('{DEL}')

class ColumnList(List):
  '''
  Multi-column list. Adapted for use with L{View.Control.List}.

  @ivar name_key: Name of the name field
  @type name_key: string
  @ivar primary_keys: Fields that will be joined as the name and used for 
    sorting
  @type primary_keys: list
  @ivar sort_col: Offset into L{primary_keys} indicating sort order column
  @type sort_col: integer
  @ivar sort_asc: True to sort ascending, False to sort descending
  @type sort_asc: boolean
  '''
  advise(instancesProvide=[IList, ISeekable, ISearchable, ISortable, 
                           IInteractive, IDetailable])
  fields_regex = re.compile('^[^:,]+: ?|,[^:,]+: ?')

  def __init__(self, context, path, name_key='Name', primary_keys=None):
    super(ColumnList, self).__init__(context, path)
    self.name_key = name_key
    self.primary_keys = primary_keys
    self.sort_col = None
    self.sort_asc = None
    
  def Activate(self):
    '''
    Sets the sort order to a known default if it hasn't been set at least once
    already.
    
    @return: Did the model activate properly?
    @rtype: boolean
    '''
    # only get context first
    if Adapter.Activate(self):
      if self.sort_col is None and self.GetItemCount() > 1:
        # sort on the name key, starting ascending
        self._SortByHeader(self.name_key, True)
    # now do selection and such to account for new sort order
    return super(ColumnList, self).Activate()
    
  def _SortByHeader(self, key, asc):
    '''
    Sorts the list using the given header as the key, either in ascending or
    descending order. This method will fail if the first and last item are equal
    since the order cannot be detected.
    
    @param key: Column key
    @type key: string
    @param asc: Sort in ascending (True) or descending (False) order?
    @type asc: boolean
    '''
    # fetch the header list
    window = self.subject.GetChildren()[self.subject.ChildCount-1]
    headers = window.GetChildren()[3].GetChildren()
    if not headers:
      return
    if key == self.name_key:
      # use the first header, always
      h = headers[0]
      h.DoDefaultAction()
    else:
      # find the header that matches the key
      for h in headers:
        if h.Name == key:
          # perform the default action on the header
          h.DoDefaultAction()
          break
    # check the new ordering on the column
    items = self.subject.GetChildren()
    first = self._GetFieldsFor(items[0])
    last = self._GetFieldsFor(items[-2])
    print asc, first[key], last[key]
    # compare ordering of first and last item
    if ((asc and (last[key] < first[key])) or 
        (not asc and (last[key] > first[key]))):
      time.sleep(0.5)
      # flip ordering if we want ascending, but we're descending
      h.DoDefaultAction()
    # update instance variables
    self.sort_col = key
    self.sort_asc = asc

  def _GetFieldsFor(self, item):
    '''
    Gets the fields for the given item, not the current selection.

    @param item: Item in the list
    @type item: pyAA.Accessible
    @return: Fields of the item keyed by their column names
    @rtype: dictionary
    '''
    s = item.Description
    d = {}
    if s is not None:
      # split the description
      keys = [k.strip(' ,:') for k in ColumnList.fields_regex.findall(s)]
      values = self.fields_regex.split(s)[1:]
      # build a dictionary of fields
      d = dict(zip(keys, values))
      # add the name field
      d[self.name_key] = item.Name or 'None'
    return d

  def _GetNameFor(self, item):
    '''
    Gets the name for the given item, not the current selection.

    @param item: Item in the list
    @type item: pyAA.Accessible
    @return: Name of the item given by the L{primary_keys} fields.
    @rtype: string
    '''
    fields = self._GetFieldsFor(item)
    if fields is not None and self.primary_keys:
      # select those of interest
      o = []
      for key in self.primary_keys:
        try:
          o.append(fields[key])
        except KeyError:
          pass
      return ', '.join(o)
    else:
      return item.Name
    
  def SortPrev(self):
    '''
    Change sort ascending or descending, or move to previous column.
    
    @return: Did sort order wrap?
    @rtype: boolean    
    '''
    wrap = False
    # if ascending
    if self.sort_asc:
      # move to previous column
      i = list(self.primary_keys).index(self.sort_col)
      wrap = (i-1 < 0)
      self.sort_col = self.primary_keys[(i-1) % len(self.primary_keys)] 
    # flip the sort
    self._SortByHeader(self.sort_col, not self.sort_asc)
    return wrap
  
  def SortNext(self):
    '''
    Change sort ascending or descending, or move to next column.
    
    @return: Did sort order wrap?
    @rtype: boolean
    '''
    wrap = False
    # if descending
    if not self.sort_asc:
      # move to next column 
      i = list(self.primary_keys).index(self.sort_col)
      l = len(self.primary_keys)
      wrap = (i+1 >= l)
      self.sort_col = self.primary_keys[(i+1) % l]      
    # flip the sort
    self._SortByHeader(self.sort_col, not self.sort_asc)
    return wrap
  
  def GetSortName(self): 
    '''
    Get the name of the sort column and whether it is ascending or descending.
    
    @return: Name of the sort order
    @rtype: string
    '''
    # build an order string
    if self.sort_asc:
      order = 'ascending'
    else:
      order = 'descending'
    return '%s %s' % (self.sort_col, order)

  def GetSelectedName(self, default=''):
    '''
    @param default: Default name to return when collection empty
    @type default: string
    @return: Values of the primary field(s) which defaults to the Name property
    @rtype: string
    '''
    # quit immediately if there is no focus
    selected = self.GetSelectedItem()
    if selected is None:
      return default
    return self._GetNameFor(selected)

  def GetFields(self):
    '''
    @return: Field values keyed by field name
    @rtype: dictionary
    '''
    selected = self.GetSelectedItem()
    return self._GetFieldsFor(selected)

  def _SearchTestStartsWith(self, curr, text):
    return self._GetNameFor(curr).lower().startswith(text.lower())

  def _SearchTestAll(self, curr, text):
    return self._GetNameFor(curr).lower().find(text.lower()) > -1

class EditableColumnList(ColumnList):
  '''
  Multi-column list with support for deletion of items. Adapted for use with
  L{View.Control.List}.
  '''
  advise(instancesProvide=[IList, IDeletable, ISeekable, ISearchable,
                           IInteractive])

  def Delete(self):
    '''
    Removes the selected item from the list.
    '''
    self.subject.SendKeys('{DEL}')

class DropDownList(List):
  '''
  Drop down list. Adapted for use with L{View.Control.List}.
  '''
  advise(instancesProvide=[IList, ISeekable, ISearchable, IInteractive])

  def ResetFocus(self):
    try:
      self.subject.Select(FOCUS)
      return True
    except pyAA.Error:
      return False

  def FirstItem(self):
    if self.ResetFocus():
      self.subject.SendKeys('{HOME}')

  def LastItem(self):
    if self.ResetFocus():
      self.subject.SendKeys('{END}')

  def NextItem(self):
    '''
    Selects the next item in the list or wraps to the first.

    Uses keystrokes instead of selection commands to avoid closing the list.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    if not self.ResetFocus():
      return False
    try:
      self.GetSelectedItem().Navigate(NEXT)
      self.subject.SendKeys('{DOWN}')
      return False
    except pyAA.Error:
      self.subject.SendKeys('{HOME}')
      return True
    except AttributeError:
      return False

  def PrevItem(self):
    '''
    Selects the previous item in the list or wraps to the last.

    Uses keystrokes instead of selection commands to avoid closing the list.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    if not self.ResetFocus():
      return False
    try:
      self.GetSelectedItem().Navigate(PREVIOUS)
      self.subject.SendKeys('{UP}')
      return False
    except pyAA.Error:
      self.subject.SendKeys('{END}')
      return True
    except AttributeError:
      return False

  def Activate(self):
    '''
    Refreshes the drop down list model. Makes the list the subject. Gets a
    reference to the drop down list button also.

    @return: Is the object alive?
    @rtype: boolean
    '''
    # skip a level of activation so we don't try to select the first item
    # until we have our references straightened out
    if not Adapter.Activate(self):
      return False
    # reference the button
    self.button = self.subject.Children[1]
    # reference the list
    self.subject = self.subject.Children[2].Children[3]
    #self.subject.FindOneChild(lambda x:
                   #x.Role == pyAA.Constants.ROLE_SYSTEM_LIST)
    # ensure the list is visible first by pressing the button
    self.button.DoDefaultAction()
    # select the first item if there is no focus
    if self.GetSelectedItem() is None and self.GetItemCount() > 0:
      self.subject.SendKeys('{HOME}')
    return True

  def Deactivate(self):
    '''Closes drop down with the current selection active.'''
    try:
      self.button.DoDefaultAction()
    except AttributeError:
      pass

  def _SearchStart(self):
    self.search_count = [0, False]
    return super(DropDownList, self)._SearchStart()

  def _SearchAhead(self, curr):
    self.search_count[0] += 1
    super(DropDownList, self)._SearchAhead(curr)

  def _SearchBehind(self, curr):
    self.search_count[0] += 1
    super(DropDownList, self)._SearchBehind(curr)

  def _SearchFirst(self, curr):
    self.search_count = [0, True]
    super(DropDownList, self)._SearchFirst(curr)

  def _SearchLast(self, curr):
    self.search_count = [0, True]
    super(DropDownList, self)._SearchFirst(curr)

  def _SearchSelectAhead(self, curr):
    if self.search_count[1]:
      self.subject.SendKeys('{HOME}')
    self.subject.SendKeys('{DOWN}'*self.search_count[0])

  def _SearchSelectBehind(self, curr):
    if self.search_count[1]:
      self.subject.SendKeys('{END}')
    self.subject.SendKeys('{UP}'*self.search_count[0])

class Tree(Collection):
  '''
  Tree of items. Adapted for use with L{View.Control.Tree}.
  '''
  advise(instancesProvide=[ITree, ISeekable, ISearchable, IInteractive,
                           IStrideable])

  def ShowChildren(self):
    '''
    Make any children of the focused node visible. Navigation to child nodes
    does not work in all cases if they are invisible.
    '''
    curr = self.GetSelectedItem()
    try:
      if curr.State & pyAA.Constants.STATE_SYSTEM_COLLAPSED:
        curr.SendKeys('{RIGHT}')
    except AttributeError:
      pass

  def GetParentName(self, default=''):
    '''
    @param default: Default string to return if tree empty
    @return: Name of the node containing this element
    @rtype: string
    '''
    try:
      curr = self.GetSelectedItem().Navigate(LEFT)
    except pyAA.Error:
      return 'root'
    except AttributeError:
      return default
    return curr.Name

  def GetLevel(self):
    '''
    @return: Current level
    @rtype: integer
    '''
    try:
      return int(self.GetSelectedItem().Value)+1
    except AttributeError:
      return 0

  def GetItemCount(self):
    '''
    @return: Number of items in this level only
    @rtype: integer
    '''
    curr = self.GetSelectedItem()
    i = self.GetIndex()+1
    while 1:
      try:
        curr = curr.Navigate(DOWN)
        i += 1
      except pyAA.Error:
        break
      except AttributeError:
        return 0
    return i

  def GetChildCount(self):
    '''
    @return: Number child items of the current item
    @rtype: integer
    '''
    # ensure children exist
    self.ShowChildren()
    try:
      curr = self.GetSelectedItem().Navigate(RIGHT)
    except (AttributeError, pyAA.Error):
      return 0
    i = 1
    while 1:
      try:
        curr = curr.Navigate(DOWN)
        i += 1
      except pyAA.Error:
        break
    return i

  def GetIndex(self):
    '''
    @return: Index relative to the first sibling in this level
    @rtype: integer
    '''
    curr = self.GetSelectedItem()
    i = 0
    while 1:
      try:
        curr = curr.Navigate(UP)
        i += 1
      except (pyAA.Error, AttributeError):
        break
    return i

  def NextItem(self):
    '''
    Selects the next item in the list or wraps to the last.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    curr = self.GetSelectedItem()
    try:
      curr = curr.Navigate(DOWN)
      res = False
    except AttributeError:
      return False
    except pyAA.Error:
      while 1:
        try:
          curr = curr.Navigate(UP)
        except pyAA.Error:
          break
      res = True
    self.SetSelectedItem(curr)
    self.ShowChildren()
    return res

  def PrevItem(self):
    '''
    Selects the previous item in the list or wraps to the last.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    curr = self.GetSelectedItem()
    try:
      curr = curr.Navigate(UP)
      res = False
    except AttributeError:
      return False
    except pyAA.Error:
      while 1:
        try:
          curr = curr.Navigate(DOWN)
        except:
          break
      res = True
    self.SetSelectedItem(curr)
    self.ShowChildren()
    return res

  def HasChildren(self):
    '''
    Does the focused node have any children?

    @return: True if it does; False if not
    @rtype: boolean
    '''
    curr = self.GetSelectedItem()
    try:
      n = curr.Navigate(NEXT)
      return n.Value > curr.Value
    except (pyAA.Error, AttributeError):
      return False

  def HasParent(self):
    '''
    Does the focused node have a parent?

    @return: True if it does; False if not
    @rtype: boolean
    '''
    try:
      self.GetSelectedItem().Navigate(LEFT)
      return True
    except (pyAA.Error, AttributeError):
      return False

  def NextLevel(self):
    '''
    Selects the first child of this item.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    if self.HasChildren():
      # navigate to the next item
      try:
        n = self.GetSelectedItem().Navigate(RIGHT)
      except (AttributeError, pyAA.Error):
        return False
      self.SetSelectedItem(n)
      self.ShowChildren()
      return True
    return False

  def PrevLevel(self):
    '''
    Selects the parent of this item.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    if self.HasParent():
      # navigate to the next item
      try:
        n = self.GetSelectedItem().Navigate(LEFT)
      except:
        return False
      self.SetSelectedItem(n)
      self.ShowChildren()
      return True
    return False

  def _SearchAhead(self, curr):
    try:
      return curr.Navigate(DOWN)
    except pyAA.Error:
      raise ValueError

  def _SearchBehind(self, curr):
    try:
      return curr.Navigate(UP)
    except pyAA.Error:
      raise ValueError

  def _SearchFirst(self, curr):
    while 1:
      try:
        curr = curr.Navigate(UP)
      except pyAA.Error:
        return curr

  def _SearchLast(self, curr):
    while 1:
      try:
        curr = curr.Navigate(DOWN)
      except pyAA.Error:
        return curr

  def _SearchSelectAhead(self, curr):
    super(Tree, self)._SearchSelectAhead(curr)
    self.ShowChildren()

  def _SearchSelectBehind(self, curr):
    super(Tree, self)._SearchSelectBehind(curr)
    self.ShowChildren()

class ButtonList(Collection):
  '''
  List of buttons. Adapted for use with L{View.Control.List}.

  @ivar curr: Index into the path list to the current button
  @type curr: integer
  @ivar cache: Cache of accessibles keyed by path
  @type cache: dictionary
  @ivar labels: Labels to use in place of those assigned to the items in the
    list. Mapping from index in list to label.
  @type labels: dictionary
  '''
  advise(instancesProvide=[IList, ISeekable, ISearchable, IInteractive])
  def __init__(self, context, path, select_hack=False, labels={}, curr=0, hack_type='left'):
    super(ButtonList, self).__init__(context, path, select_hack, hack_type)
    self.curr = curr
    self.cache = {}
    self.labels = labels

  def Activate(self):
    '''
    Uses the context as the subject since the buttons are separate widgets.

    @return: Was the subject retrieved?
    @type: boolean
    '''
    self.cache = {}
    self.subject = self.context
    if self.subject is not None:
      self.SetSelectedItem(self.GetItem(self.curr))
      return True
    else:
      return False

  def _GetItemName(self, index):
    '''
    Gets the name of the item at index, taking labels into account.

    @param index: Index of a button in the L{path} list
    @type index: integer
    @return: Value of the name property
    @rtype: string or None
    '''
    try:
      # we check name first to make sure the item still exists; seems backward
      # but it's correct
      name = self.GetItem(index).Name
    except (pyAA.Error, AttributeError):
      return ''
    try:
      # now we check our manual labels
      return self.labels[index]
    except KeyError:
      return name

  def GetItem(self, index):
    '''
    Gets the item at the given index. Checks the local cache first to see if
    there's a live accessible.

    @param index: Index of a button in the L{path} list
    @type index: integer
    @return: Item at the given index
    @rtype: pyAA.AccessibleObject or None
    '''
    try:
      acc = self.cache[self.path[index]]
      # query for name to test liveliness
      acc.Name
      return acc
    except (pyAA.Error, KeyError):
      pass
    try:
      acc = IContext(self.subject).GetObjectAt(self.path[index])
      self.cache[self.path[index]] = acc
      return acc
    except (pyAA.Error, AttributeError, IndexError):
      return None

  def GetSelectedName(self, default=''):
    '''
    Gets the name of the selected focused item in the collection.

    @param default: Default name to return when collection empty
    @type default: string
    @return: Value of the name property
    @rtype: string or None
    '''
    try:
      # we check name first to make sure the item still exists; seems backward
      # but it's correct
      name = self.GetSelectedItem().Name
    except (pyAA.Error, AttributeError):
      return default
    try:
      # now we check our manual labels
      return self.labels[self.GetIndex()]
    except KeyError:
      return name

  def GetSelectedItem(self):
    '''
    @return: Item that has the focus
    @rtype: pyAA.AccessibleObject or None
    '''
    return self.GetItem(self.curr)

  def SetSelectedItem(self, item):
    '''
    Gives focus to the given button. Does it twice to account for selection
    changing on first but not focus.

    @param item: Item to select
    @type item: pyAA.AccessibleObject
    '''
    item.Select(FOCUS)
    item.Select(FOCUS)

  def GetItemCount(self):
    '''
    @return: Number of child items in the collection
    @rtype: integer
    '''
    return len(self.path)

  def GetIndex(self):
    '''
    @return: Index of the focused item
    @rtype: integer
    '''
    return self.curr

  def FirstItem(self):
    '''
    Selects the first item in the list.

    @return: Was the first item selected?
    @rtype: boolean
    '''
    try:
      c = self.GetItem(0)
      self.SetSelectedItem(c)
    except (AttributeError, pyAA.Error):
      return False
    self.curr = 0
    return True

  def LastItem(self):
    '''
    Selects the last item in the list.

    @return: Was the last item selected?
    @rtype: boolean
    '''
    try:
      c = self.GetItem(self.GetItemCount()-1)
      self.SetSelectedItem(c)
    except (AttributeError, pyAA.Error):
      return False
    self.curr = len(self.path)-1
    return True

  def NextItem(self):
    '''
    Selects the next item in the list or wraps to the first.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    curr = (self.curr + 1) % self.GetItemCount()
    rv = curr < self.curr
    self.curr = curr
    try:
      n = self.GetItem(self.curr)
      self.SetSelectedItem(n)
    except (pyAA.Error, AttributeError):
      return False
    return rv

  def PrevItem(self):
    '''
    Selects the previous item in the list or wraps to the last.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    curr = (self.curr - 1) % self.GetItemCount()
    rv = curr > self.curr
    self.curr = curr
    try:
      n = self.GetItem(self.curr)
      self.SetSelectedItem(n)
    except (pyAA.Error, AttributeError):
      return False
    return rv

  def _SearchStart(self):
    '''
    Callback for L{CircularSearch}. Gets the currently selected item.

    @return: Currently selected item index
    @rtype: integer
    '''
    return self.curr

  def _SearchAhead(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the next item to test.

    @param curr: Currently selected item index
    @type curr: integer
    @return: Next item index to test
    @rtype: integer
    @raise ValueError: When the next item does not exist
    '''
    if curr + 1 >= self.GetItemCount():
      raise ValueError
    else:
      return curr + 1

  def _SearchBehind(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the previous item to test.

    @param curr: Currently selected item index
    @type curr: integer
    @return: Previous item index to test
    @rtype: integer
    @raise ValueError: When the previous item does not exist
    '''
    if curr - 1 < 0:
      raise ValueError
    else:
      return curr - 1

  def _SearchFirst(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the first item.

    @param curr: Current item index to test
    @type curr: integer
    @return: Next item index to test
    @rtype: integer
    @raise ValueError: When the first item does not exist
    '''
    return 0

  def _SearchLast(self, curr):
    '''
    Callback for L{CircularSearch}. Moves to the last item.

    @param curr: Current item index to test
    @type curr: integer
    @return: Next item index to test
    @rtype: integer
    @raise ValueError: When the last item does not exist
    '''
    return self.GetItemCount() - 1

  def _SearchSelectAhead(self, curr):
    '''
    Callback for L{CircularSearch}. Selects the current item when searching
    ahead.

    @param curr: Current item index to select
    @type curr: integer
    '''
    try:
      c = self.GetItem(curr)
    except pyAA.Error:
      return
    self.SetSelectedItem(c)
    self.curr = curr

  def _SearchSelectBehind(self, curr):
    '''
    Callback for L{CircularSearch}. Selects the current item when searching
    behind.

    @param curr: Current item index to select
    @type curr: integer
    '''
    try:
      c = self.GetItem(curr)
    except pyAA.Error:
      return
    self.SetSelectedItem(c)
    self.curr = curr

  def _SearchTestStartsWith(self, curr, text):
    '''
    Callback for L{CircularSearch}. Checks if the current item starts with the
    given text.

    @param curr: Current item index to test
    @type curr: index
    @param text: Search string
    @type text: string
    @return: The current item starts with the given text?
    @rtype: boolean
    '''
    return self._GetItemName(curr).lower().startswith(text.lower())

  def _SearchTestAll(self, curr, text):
    '''
    Callback for L{CircularSearch}. Checks if the current item contains all of
    the given text.

    @param curr: Current item index to test
    @type curr: index
    @param text: Search string
    @type text: string
    @return: The current item contains the given text?
    @rtype: boolean
    '''
    print 'target: %s, index: %s, label: %s' % (text, curr, self._GetItemName(curr))
    return self._GetItemName(curr).lower().find(text.lower()) > -1

  def SearchStart(self):
    '''
    Stores the item which was selected when search started.
    '''
    self.search_anchor = (self.curr, self.GetSelectedItem())

  def SearchReset(self):
    '''
    Resets the current item to the one that was selected when the search began.
    '''
    self.curr = self.search_anchor[0]
    self.SetSelectedItem(self.search_anchor[1])

class CheckBox(Adapter):
  '''
  Simple checkbox. Adapted for use with L{View.Control.List}.
  '''
  advise(instancesProvide=[IList, ISeekable, IInteractive])
  choices = ['no', 'yes']

  def GetSelectedName(self, default=''):
    '''
    @param default: Default name to return when collection empty
    @type default: string
    @return: Value of the name property
    @rtype: string or None
    '''
    try:
      return self.choices[self.GetSelectedItem()]
    except pyAA.Error:
      return default

  def GetSelectedItem(self):
    '''
    @return: Is the box checked?
    @rtype: boolean or None
    '''
    try:
      return bool(self.subject.State & pyAA.Constants.STATE_SYSTEM_CHECKED)
    except pyAA.Error:
      return None

  def GetItemCount(self):
    '''
    @return: Always zero so the item count isn't announced
    @rtype: number
    '''
    return 0

  def GetIndex(self):
    '''
    @return: Index of the focused item
    @rtype: integer
    '''
    return 0 #self.GetSelectedItem()+1

  def FirstItem(self):
    '''
    Selects the no option.

    @return: Was the first item selected?
    @rtype: boolean
    '''
    if self.GetSelectedItem():
      try:
        self.subject.DoDefaultAction()
      except pyAA.Error:
        return False
    return True

  def LastItem(self):
    '''
    Selects the yes option.

    @return: Was the first item selected?
    @rtype: boolean
    '''
    if not self.GetSelectedItem():
      try:
        self.subject.DoDefaultAction()
      except pyAA.Error:
        return False
    return True

  def NextItem(self):
    '''
    Selects the alternative value, False if True or True if False.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    try:
      self.subject.DoDefaultAction()
    except pyAA.Error:
      pass
    return False

  def PrevItem(self):
    '''
    Selects the alternative value, False if True or True if False.

    @return: Did the selection wrap?
    @rtype: boolean
    '''
    try:
      self.subject.DoDefaultAction()
    except pyAA.Error:
      pass
    return False

  def SeekToItem(self, char):
    '''
    Selects yes or no based on the given character.

    @param char: Character of interest
    @type char: string
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    if char == 'y':
      self.LastItem()
    elif char == 'n':
      self.FirstItem()
    else:
      return None
