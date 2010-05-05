'''
Defines classes for browsing collections of items like lists or trees.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import Base, Output, Support, Interface

class Collection(Base.Control): 
  '''
  Virtual class. Collection of items. Model must implement IInteractive, 
  IInfiniteCollection. ISeekable and IFiniteCollection are optional.
  
  @ivar label: Label for collection items
  @type label: string
  '''
  def __init__(self, parent, model, name, label, default_name):
    '''
    Initializes an instance.
    
    See instance variables for parameter descriptions.
    '''
    super(Collection, self).__init__(parent, model, name, default_name)
    self.label = label
       
  def OnActivate(self, message, auto_focus):
    '''
    Ensures the control is ready and an item is selected.
    
    Plays OutIntroduction.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean    
    @return: Is the control ready for interaction?
    @rtype: boolean
    '''
    if super(Collection, self).OnActivate(message, auto_focus):
      p = self.OutIntroduction(message, auto_focus)
      self.Output(self, p)
      if not auto_focus:
        self.NotifyAboutChange()
      return True
    else:
      return False
      
  def OnPrevHigh(self, message):
    '''
    Selects the first item in the collection
    
    Plays OutFirstItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      exist = Interface.IFiniteCollection(self.model).FirstItem()
    except NotImplementedError:
      p = self.OutNotImplemented(message, 
                                 'Skipping to the first item is not possible.')
      self.Output(self, p)
    else:
      if exist:
        p = self.OutFirstItem(message)
        self.NotifyAboutChange()
        self.Output(self, p)
      
  def OnPrevMid(self, message):
    '''
    Selects the previous item in the collection.
    
    Plays OutWrapItem or OutCurrentItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    wrap = Interface.IInfiniteCollection(self.model).PrevItem()
    if wrap:
      p = self.OutWrapItem(message)
    else:
      p = self.OutCurrentItem(message)
    self.Output(self, p)
    self.NotifyAboutChange()

  def OnNextMid(self, message):
    '''
    Selects the next item in the collection.
    
    Plays OutWrapItem or OutCurrentItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    wrap = Interface.IInfiniteCollection(self.model).NextItem()
    if wrap:
      p = self.OutWrapItem(message)
    else:
      p = self.OutCurrentItem(message)
    self.Output(self, p)
    self.NotifyAboutChange()
    
  def OnText(self, message):
    '''
    Selects the next item in the collection beginning with the pressed 
    character.
    
    Plays OutNotImplemented, OutWrapSeekItem, OutSeekItem, or OutNoSeekItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}    
    '''
    try:
      r = Interface.ISeekable(self.model).SeekToItem(message.Char)
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Seeking by letter is not available.')
    else:
      if r == True:
        p = self.OutWrapSeekItem(message, message.Char)
      elif r == False:
        p = self.OutSeekItem(message, message.Char)
      else:
        p = self.OutNoSeekItem(message, message.Char)
      self.NotifyAboutChange()
    self.Output(self, p)
    
  def OnMoreInfo(self, message):
    '''
    Gives more information about the selected item.
    
    Calls OutDetailCurrent.
    
    @param message: Input message that triggered this event handler
    @type message: L{Input.Messages.InboundMessage}
    '''
    p = self.OutDetailCurrent(message)
    self.Output(self, p)
    
    
  def OutCurrentItem(self, message):
    '''
    Virtual method. Outputs information about the current item.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    return None
    
  def OutFirstItem(self, message):
    '''
    Outputs the information about the first item.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    return None
    
  def OutWrapItem(self, message):
    '''
    Virtual method. Outputs information about the current item that was selected
    by wrapping past a collection bound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass
    
class List(Collection):
  '''
  Linear list of selectable items. Model must implement IInteractive and
  IInfiniteCollection. ISeekable, IList, IDeleteable, and IDetailable are 
  optional.
  
  @ivar order: Order in which fields should be reported
  @type order: list
  '''
  def __init__(self, parent, model, name='', label='item', order=None):
    '''
    Initializes an instance.
    
    See instance variables for parameter descriptions.
    '''
    super(List, self).__init__(parent, model, name, label, default_name='list')
    self.empty = 'The %s list is empty.'
    self.order = order
  
  def GetSpeakableIndex(self):
    '''
    @return: Speakable description of the index of the current element
    @rtype: string
    '''
    try:
      m = Interface.IFiniteCollection(self.model)
    except NotImplementedError:
      return ''
    if m.GetItemCount() > 0:
      return '%s %d of %d' % (self.label, m.GetIndex()+1, m.GetItemCount())
    else:
      return ''
    
  def OnNextHigh(self, message):
    '''
    Changes the sort order of the list if possible.
    
    Plays OutNotImplemented, OutCurrentSort, OutWrapSort.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      wrap = Interface.ISortable(self.model).SortPrev()
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Sorting not available.')
    else:
      if wrap:
        p = self.OutWrapSort(message)
      else:
        p = self.OutCurrentSort(message)
    self.Output(self, p)

  def OnNextLow(self, message):
    '''
    Changes the sort order of the list if possible.
    
    Plays OutNotImplemented, OutCurrentSort, OutWrapSort.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      wrap = Interface.ISortable(self.model).SortNext()
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Sorting not available.')
    else:
      if wrap:
        p = self.OutWrapSort(message)
      else:
        p = self.OutCurrentSort(message)
    self.Output(self, p)    
    
  def OnPrevLow(self, message):
    '''
    Selects the last item in the collection
    
    Plays OutNotImplemented, OutCurrentItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      exist = Interface.IList(self.model).LastItem()
    except NotImplementedError:
      p = self.OutNotImplemented(message, 
                                 'Skipping to the last item is not possible.')
      self.Output(self, p)
    else:
      if exist:
        p = self.OutLastItem(message)
        self.NotifyAboutChange()
        self.Output(self, p)
    
  def OnDelete(self, message):
    '''
    Deletes an item from the list if deletion is allowed.
    
    Calls OutNotImplemented, OutDeleteItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      m = Interface.IDeletable(self.model)
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Deletion is not available.')
    else:
      m.Delete()
      p = self.OutDeleteItem(message)
      self.NotifyAboutChange()
    self.Output(self, p)

  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the name of the list, the index of the current item, and the name
    of the current item.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    # the control exists, tell the user about it
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech='%s, %s' % (self.Name, self.GetSpeakableIndex()), 
                 sound=Output.ISound(self).Action('start'),
                 person=Output.SUMMARY),
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    return p
      
  def OutDeadLong(self, message):
    '''
    Outputs a message stating the list is not available.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    # the control is missing, inform the user
    p = Output.Packet(self, message)
    p.AddMessage(speech='The list of %s is not available' % self.Name, 
                 person=Output.SUMMARY)
    return p
    
  def OutChange(self, message):
    '''
    Outputs the number of items or the currently selected item.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    try:
      # report the number of items in the list if it is finite
      m = Interface.IFiniteCollection(self.model)
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   person=Output.SUMMARY,
                   speech='%d items in %s' % (m.GetItemCount(), self.Name))
    except NotImplementedError:
      # report the selected item if infinite
      m = Interface.IInfiniteCollection(self.model)
      p.AddMessage(sound=Output.ISound(self).Action('start'),
                   person=Output.SUMMARY,
                   speech=m.GetSelectedName(self.empty % self.Name))
    return p
  
  def OutCurrentSort(self, message):
    '''
    Outputs the name of the current sort key.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ISortable(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSortName(), person=Output.SUMMARY)
    return p
    
  def OutCurrentItem(self, message):
    '''
    Outputs the name of the current item.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    return p
    
  def OutLastItem(self, message):
    '''
    Outputs the name of the current item and its index.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    p.AddMessage(speech=self.GetSpeakableIndex(), person=Output.SUMMARY)
    return p
    
  def OutFirstItem(self, message):
    '''
    Outputs the name of the current item and its index.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    p.AddMessage(speech=self.GetSpeakableIndex(), person=Output.SUMMARY)
    return p
    
  def OutSeekItem(self, message, text):
    '''
    Outputs the name of the current item and its index.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    p.AddMessage(speech=self.GetSpeakableIndex(), person=Output.SUMMARY)
    p2 = Output.Packet(self, message, group=Output.NARRATOR)
    p2.AddMessage(speech=text, letters=True)
    return p, p2

  OutSearchItem = OutSeekItem
    
  def OutWrapSeekItem(self, message, text):
    '''
    Outputs the name of the current item, its index, and the wrap sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name),
                 person=Output.CONTENT)
    p.AddMessage(speech=self.GetSpeakableIndex(), 
                 sound=Output.ISound(self).Action('wrap'),
                 person=Output.SUMMARY)
    p2 = Output.Packet(self, message, group=Output.NARRATOR)
    p2.AddMessage(speech=text, letters=True)
    return p, p2    

  OutWrapSearchItem = OutWrapSeekItem
    
  def OutWrapItem(self, message):
    '''
    Outputs the name of the current item and the wrap sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name),
                 person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('wrap'),
                 person=Output.SUMMARY)
    return p
  
  def OutWrapSort(self, message):
    '''
    Outputs the name of the current sort key.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ISortable(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSortName(),
                 sound=Output.ISound(self).Action('wrap'),
                 person=Output.SUMMARY)
    return p
    
  @Support.generator_method('List')
  def OutDetailCurrent_gen(self, message):
    '''
    Outputs the name of the item and the index of the item.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    yield p
    p = Output.Packet(self, message, listen=True, name='details') 
    p.AddMessage(speech=self.GetSpeakableIndex(), person=Output.SUMMARY)
    yield p
    try:
      m = Interface.IDetailable(self.model)
    except NotImplementedError:
      return
    fields = m.GetFields()
    # put all field names in desired order
    if self.order is not None:
      order = self.order + [f for f in fields if f not in self.order]
    else:
      # otherwise, sort alphabetically
      order = fields.keys()
      order.sort()
    # speak every name/value pair one at a time
    for name in order:
      try:
        # ignore keys that do not exist
        value = fields[name]
      except KeyError:
        continue
      p = Output.Packet(self, message, listen=True, name='details')
      p.AddMessage(speech='%s: %s' % (name, value), person=Output.CONTENT)
      yield p
    
  def OutDeleteItem(self, message):
    '''
    Ouputs the name of the newly selected item and the deletion sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IInfiniteCollection(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('delete'),
                 person=Output.SUMMARY)
    return p
    
  def OutWhereAmI(self, message):
    '''
    Outputs the name and sound of the list.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = super(List, self).OutWhereAmI(message)
    s = 'browsing the %s list' % self.Name
    p.AddMessage(speech=s, sound=Output.ISound(self).Action('start'),
                 person=Output.SUMMARY)
    return p
  
class StridedList(List):
  '''
  Linear list of selectable items that can be navigated at multiple levels. 
  Model must implement IInteractive, IInfiniteCollection, and IStrideable. 
  ISeekable, IList, IDeleteable, and IDetailable are optional.
  '''
  def GetSpeakableLevel(self):
    '''
    @return: Speakable description of the current level
    @rtype: string
    '''
    return 'browsing by %s' % Interface.IStrideable(self.model).GetLevel()
  
  def GetSpeakableIndex(self):
    '''
    Gets the same value returned by GetSpeakableLevel. This method only exists
    to enable the easy reuse of OutDetailCurrent_gen from the parent class.
    
    @return: Speakable description of the current level
    @rtype: string
    '''
    return self.GetSpeakableLevel()
  
  def OnLow(self, message):
    '''
    Selects the next smaller stride level.
    
    Plays OutNextLevel or OutSmallestStride.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if Interface.IStrideable(self.model).NextLevel():
      p = self.OutNextLevel(message)
      self.NotifyAboutChange()
    else:
      p = self.OutSmallestStride(message)
    self.Output(self, p)
  
  def OnHigh(self, message):
    '''
    Selects the next larger stride level.
    
    Plays OutPrevLevel or OutLargestStride.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    if Interface.IStrideable(self.model).PrevLevel():
      p = self.OutPrevLevel(message)
      self.NotifyAboutChange()
    else:
      p = self.OutLargestStride(message)
    self.Output(self, p)

  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the name of the list, the current stride level, and the name of the 
    current item.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.IStrideable(self.model)
    p = Output.Packet(self, message)
    p.AddMessage(speech='%s, %s' % (self.Name, self.GetSpeakableLevel()), 
                 sound=Output.ISound(self).Action('start'),
                 person=Output.SUMMARY)
    m = Interface.IInfiniteCollection(self.model)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), 
                 person=Output.CONTENT)
    return p
        
  def OutNextLevel(self, message):
    '''
    Outputs the name of the next stride level and the next level sound. 
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(speech=self.GetSpeakableLevel(), person=Output.SUMMARY,
                 sound=Output.ISound(self).Action('next'))
    return p
  
  def OutPrevLevel(self, message):
    '''
    Outputs the name of the previous stride level and the next level sound. 
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(speech=self.GetSpeakableLevel(), person=Output.SUMMARY,
                 sound=Output.ISound(self).Action('previous'))
    return p
  
  def OutSmallestStride(self, message):
    '''
    Outputs the smallest stride level reached sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('last'),
                 person=Output.SUMMARY)
    return p

  def OutLargestStride(self, message):
    '''
    Outputs the largest stride level reached sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('first'),
                 person=Output.SUMMARY)
    return p

class Tree(Collection):
  '''
  Hierarchy of nested lists. Model must implment IInteractive, ITree, ISeekable,
  and IStrideable.
  '''
  def __init__(self, parent, model, name='', label='sibling'):
    '''
    Initializes an instance.
    
    See instance variables for parameter description.
    '''
    super(Tree, self).__init__(parent, model, name, label, default_name='tree')
    self.empty = 'The %s tree is empty.'

  def GetSpeakableLevel(self):
    '''
    @return: Speakable description of the current level
    @rtype: string
    '''
    return 'level %d' % Interface.IStrideable(self.model).GetLevel()
    
  def GetSpeakableIndex(self):
    '''
    @return: Speakable description of the index of the current element
    @rtype: string
    '''
    m = Interface.IFiniteCollection(self.model)
    c = m.GetItemCount()
    if c > 0:
      return '%s %d of %d' % (self.label, m.GetIndex()+1, c)
    else:
      return ''
    
  def GetSpeakableChildCount(self):
    '''
    @return: Speakable description of the number of children of the current item
    @rtype: string
    '''
    children = Interface.ITree(self.model).GetChildCount()
    if children > 0:
      return '%d children' % children
    else:
      return ''

  def OnLow(self, message):
    '''
    Navigates to a lower level in the tree.
    
    Plays OutNextLevel or OutLeafOfTree.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''           
    if Interface.IStrideable(self.model).NextLevel():
      # report current item name, level and children
      p = self.OutNextLevel(message)
      self.NotifyAboutChange()      
    else:
      p = self.OutLeafOfTree(message)
    self.Output(self, p)

  def OnHigh(self, message):
    '''
    Navigates to a higher level in the tree.
    
    Plays OutPrevLevel or OutRootOfTree.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.MessagesInboundMessage}
    '''           
    if Interface.IStrideable(self.model).PrevLevel():
      # report current item name, level and children
      p = self.OutPrevLevel(message)
      self.NotifyAboutChange()
    else:
      p = self.OutRootOfTree(message)
    self.Output(self, p)
    
  def OutIntroduction(self, message, auto_focus):
    '''
    Outputs the name of the tree, the index of the current item, the level of
    the current item, and the name of the current item.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did this object receive the focus automatically?
    @type auto_focus: boolean
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    # the control exists, tell the user about it
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None
    p = Output.Packet(self, message)
    s = '%s, %s, %s' % (self.Name, self.GetSpeakableLevel(),
                        self.GetSpeakableIndex())
    p.AddMessage(speech=s, sound=Output.ISound(self).Action('start'),
                 person=Output.SUMMARY)
    if m.GetItemCount() == 0:
      s = ''
    else:
      s = '%s, in %s'% (m.GetSelectedName(self.empty % self.Name),
                        m.GetParentName())
    p.AddMessage(speech=s, sound=sound, person=Output.CONTENT)
    return p
    
  def OutDeadLong(self, message):
    '''
    Outputs a message stating the list is not available.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    # the control is missing, inform the user
    p = Output.Packet(self, message)
    p.AddMessage(speech='The tree of %s is not available' % self.Name)
    return p
    
  def OutRootOfTree(self, message):
    '''
    Outputs the root of tree sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('first'),
                 person=Output.SUMMARY)
    return p
    
  def OutLeafOfTree(self, message):
    '''
    Outputs the leaf of tree sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    ''' 
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('last'),
                 person=Output.SUMMARY)
    return p
    
  def OutNextLevel(self, message):
    '''
    Outputs the name of the selected item, the number of children of the 
    current item, the level of the current item, the index of the item among
    its siblings, and the next level sound. Plays the children indicator too
    if the item has children.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None
    p = Output.Packet(self, message)
    p.AddMessage(speech = '%s, %s' % (self.GetSpeakableLevel(), 
                                      self.GetSpeakableIndex()),
                 person=Output.SUMMARY, 
                 sound=Output.ISound(self).Action('next'))
    p.AddMessage(speech='%s, in %s' % (m.GetSelectedName(self.empty % self.Name), 
                                       m.GetParentName()),
                 sound=sound, person=Output.CONTENT)
    return p
    
  def OutPrevLevel(self, message):
    '''
    Outputs the name of the selected item, the number of children of the 
    current item, the level of the current item, the index of the item among
    its siblings, and the previous level sound. Plays the children indicator too
    if the item has children.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None    
    p = Output.Packet(self, message)
    p.AddMessage(speech = '%s, %s' % (self.GetSpeakableLevel(), 
                                      self.GetSpeakableIndex()),
                 person=Output.SUMMARY, 
                 sound=Output.ISound(self).Action('previous'))
    p.AddMessage(speech='%s, in %s' % (m.GetSelectedName(self.empty % self.Name), 
                                       m.GetParentName()),
                 sound=sound, person=Output.CONTENT)
    return p
    
  def OutFirstItem(self, message):
    '''
    Outputs the name of the selected item, the number of children of the 
    current item, the level of the current item, the index of the item among
    its siblings, and the previous level sound. Plays the children indicator too
    if the item has children.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None
    p = Output.Packet(self, message)
    p.AddMessage(speech = '%s, %s' % (self.GetSpeakableLevel(), 
                                      self.GetSpeakableIndex()),
                 person=Output.SUMMARY,
                 sound=Output.ISound(self).Action('previous'))
    p.AddMessage(speech='%s, in %s' % (m.GetSelectedName(self.empty % self.Name), 
                                       m.GetParentName()),
                 sound=sound, person=Output.CONTENT)
    return p
    
  @Support.generator_method('Tree')
  def OutDetailCurrent_gen(self, message):
    '''
    Outputs the name of the current selection; its child count, level, and 
    index; and its containing element.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None    
    # speak the item name
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech='%s, in %s' % (m.GetSelectedName(self.empty % self.Name), 
                                       m.GetParentName()),
                 sound=sound, person=Output.CONTENT)
    yield p
    # then its location
    p = Output.Packet(self, message, listen=True, name='details')
    p.AddMessage(speech='%s, %s, %s' % (self.GetSpeakableChildCount(),
                                        self.GetSpeakableLevel(),
                                        self.GetSpeakableIndex()),
                 person=Output.SUMMARY)
    yield p
    
  def OutSeekItem(self, message, text):
    '''
    Outputs the name of the selected item, the number of children of the 
    current item, the level of the current item, the index of the item among
    its siblings, and the has children sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None    
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), sound=sound, 
                 person=Output.CONTENT)
    p2 = Output.Packet(self, message, group=Output.NARRATOR)
    p2.AddMessage(speech=text, letters=True)
    return p, p2
    
  def OutWrapSeekItem(self, message, text):
    '''
    Outputs the name of the selected item, the number of children of the 
    current item, the level of the current item, the index of the item among
    its siblings, the has children sound, and the wrap sound.
        
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Packet of information to be output
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), sound=sound, 
                 person=Output.CONTENT)
    p.AddMessage(person=Output.SUMMARY, 
                 sound=Output.ISound(self).Action('wrap'))
    p2 = Output.Packet(self, message, group=Output.NARRATOR)
    p2.AddMessage(speech=text, letters=True)
    return p, p2
    
  def OutWrapItem(self, message):
    '''
    Outputs the name of the current item, the wrap sound, and the has children
    sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None
    p = Output.Packet(self, message)      
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), sound=sound,
                 person=Output.CONTENT)
    p.AddMessage(sound=Output.ISound(self).Action('wrap'),person=Output.SUMMARY)
    return p
    
  def OutCurrentItem(self, message):
    '''
    Outputs the name of the current item and the has children sound.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    if m.HasChildren():
      sound = Output.ISound(self).State('navigable')
    else:
      sound = None
    p = Output.Packet(self, message)
    p.AddMessage(speech=m.GetSelectedName(self.empty % self.Name), sound=sound, 
                 person=Output.CONTENT)
    return p
    
  def OutChange(self, message):
    '''
    Outputs the name of the selected item.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    m = Interface.ITree(self.model)
    # report the name of the selected item
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).Action('start'),
                 person=Output.SUMMARY,
                 speech='%s selected in %s' % 
                 (m.GetSelectedName(self.empty % self.Name), self.Name))
    return p
    
  def OutWhereAmI(self, message):
    '''
    Outputs the name and sound of the tree.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = super(Tree, self).OutWhereAmI(message)
    s = 'browsing the %s tree' % self.Name
    p.AddMessage(speech=s, sound=Output.ISound(self).Action('start'),
                 person=Output.SUMMARY)
    return p
  
if __name__ == '__main__':
  pass
  
