'''
Defines the parent class for all controls.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import View, Output, Interface, Support

class Control(View.Base):
  '''
  Most base control pattern definition. Establishes a connection with a GUI 
  component when activated.
  
  @ivar name: Developer given name for this L{Control}
  @type name: string
  @ivar default_name: Default name to use when no other name is available
  @type default_name: string
  @ivar search: List of characters comprising the current search string
  @type search: list
  '''
  def __init__(self, parent, model, name, default_name):
    '''
    Initializes the object.

    See instance variables for parameter descriptions.
    '''
    super(Control, self).__init__(parent, model)
    self.name = name
    self.default_name = default_name
    self.search = []
    
  def getName(self):
    '''
    Gets the name of this L{Control} to report to the user. Prefers the name
    explicitly set when this L{View} is created. If a name isn't specified, the
    name given by the L{Interface.IInterative} is used instead.
    
    @return: Name to report to the user
    @rtype: string
    '''
    return Interface.IInteractive(self.model).GetName(self.name, 
                                                      self.default_name)
  
  def setName(self, name):
    '''
    Sets the explicit name of this L{Control} that will be preferred when 
    reporting the name to a user.
    
    @param name: Name of this L{Control}
    @type name: string
    '''
    self.name = name
  Name = property(getName, setName)
    
  def OnActivate(self, message, auto_focus):
    '''
    Calls OnGainFocus when ready and activated.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param auto_focus: Did the object receive focus automatically?
    @type auto_focus: boolean
    @return: Did the model activate?
    @rtype: boolean
    '''
    if super(Control, self).OnActivate(message, auto_focus):
      self.OnGainFocus(message)
      return True
    
  def OnPacketDone(self, message):
    '''
    Speaks the next detail about the current context.
    
    Calls OutDetailCurrent.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    '''
    if message.Packet.Name == 'details':
      p = self.OutDetailCurrent(message)
      self.Output(self, p)
    
  def OnPacketPreempt(self, message):
    '''
    Resets the generator responsible for giving information about the current
    context.
    
    @param message: Packet message that triggered this event handler
    @type message: L{Output.Messages.PacketMessage}
    '''
    if message.Packet.Name != 'details':
      self.OutDetailCurrent_gen(message, reset_gen=True)
      
  def OnIndirectChange(self, message):
    '''
    Checks if the model has changed in response to some other L{View} object
    changing. If it has, call OutChange.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # check if the model has changed
    if Interface.IInteractive(self.model).HasChanged():
      # output a notification of the change
      p = self.OutChange(message)
      self.Output(self, p)
      
  def OnSearch(self, message):
    '''
    Indicates the start or end of a search.
    
    Calls OutNotImplemented, OutStartSearch, OutCurrentItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      m = Interface.ISearchable(self.model)
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Full text search is not available.')
    else:
      if message.Press:
        m.SearchStart()
        p = self.OutStartSearch(message)
      elif self.search:
        p = self.OutEndSearch(message)
      else:
        m.SearchReset()
        p = self.OutEndSearch(message)
      # reset the current search string
      self.search = []        
    self.Output(self, p)
    
  def OnTextSearch(self, message):
    '''
    Adds the pressed character to the search string and finds the next match.
    
    Calls OutNotImplemented, OutSearchItem, OutWrapSearchItem, OutNoSearchItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      m = Interface.ISearchable(self.model)
    except NotImplementedError:
      if message.Press:
        p=self.OutNotImplemented(message, 'Full text search is not available.')
      else:
        p = None
    else:
      # add the character to our search string
      self.search.append(message.Char)
      # navigate to the next match
      text = ''.join(self.search)
      rv = m.SearchForNextMatch(text, True)
      if rv == False:
        # next match found without wrapping
        p = self.OutSearchItem(message, text)
        self.NotifyAboutChange()
      elif rv == True:
         # next match found after wrapping
        p = self.OutWrapSearchItem(message, text)
        self.NotifyAboutChange()
      elif rv is None:
        # match not found, pop the last char off
        #self.search.pop()
        p = self.OutNoSearchItem(message, text)
    self.Output(self, p)
  
  def OnNextSearch(self, message):
    '''
    Finds the next match for the current search string.
    
    Calls OutNotImplemented, OutSearchItem, OutWrapSearchItem, OutNoSearchItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      m = Interface.ISearchable(self.model)
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Full text search is not available.')
    else:
      # navigate to the next match
      text = ''.join(self.search)
      rv = m.SearchForNextMatch(text, False)
      if rv == False:
        # next match found without wrapping
        p = self.OutSearchItem(message, '')
        self.NotifyAboutChange()
      elif rv == True:
         # next match found after wrapping
        p = self.OutWrapSearchItem(message, '')
        self.NotifyAboutChange()
      elif rv is None:
        # match not found
        p = self.OutNoSearchItem(message, text)
    self.Output(self, p)
  
  def OnPrevSearch(self, message):
    '''
    Finds the previous match for the current search string.
    
    Calls OutNotImplemented, OutSearchItem, OutWrapSearchItem, OutNoSearchItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      m = Interface.ISearchable(self.model)
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Full text search is not available.')
    else:
      # navigate to the previous match
      text = ''.join(self.search)
      rv = m.SearchForPrevMatch(text, False)
      if rv == False:
        # prev match found without wrapping
        p = self.OutSearchItem(message, '')
        self.NotifyAboutChange()
      elif rv == True:
         # prev match found after wrapping
        p = self.OutWrapSearchItem(message, '')
        self.NotifyAboutChange()
      elif rv is None:
        # match not found
        p = self.OutNoSearchItem(message, text)
    self.Output(self, p)
 
  def OnBackspaceSearch(self, message):
    '''
    Removes the last character from the search string and finds the previous
    match.
    
    Calls OutNotImplemented, OnPrevSearch.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    try:
      m = Interface.ISearchable(self.model)
    except NotImplementedError:
      p = self.OutNotImplemented(message, 'Full text search is not available.')
    else:
      # remove the last character from the search string
      try:
        self.search.pop()
      except IndexError:
        pass
      if self.search:
        # navigate to the previous match
        text = ''.join(self.search)
        rv = m.SearchForPrevMatch(text, False)
        if rv == False:
          # prev match found without wrapping
          p = self.OutSearchItem(message, text)
          self.NotifyAboutChange()
        elif rv == True:
          # prev match found after wrapping
          p = self.OutWrapSearchItem(message, text)
          self.NotifyAboutChange()
        else:
          p = self.OutNoSearchItem(message, text)
      else:
        # return to the item where the search started
        m.SearchReset()
        p = self.OutCurrentItem(message)
        self.NotifyAboutChange()
    self.Output(self, p)
    
  def OutCurrentItem(self, message):
    '''
    Virtual method. Outputs information about the current item.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass

  def OutSeekItem(self, message, text):
    '''
    Virtual method. Outputs information about the current item selected by seek.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass

  OutSearchItem = OutSeekItem
    
  def OutWrapSeekItem(self, message, text):
    '''
    Virtual method. Outputs information about the current item selected by a
    seek that wraps past the end of the collection.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass

  OutWrapSearchItem = OutWrapSeekItem
    
  def OutNoSeekItem(self, message, text):
    '''
    Outputs a sound indicating an item is missing.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param text: Text to seek
    @type text: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('missing'),
                 person=Output.CONTENT)
    p2 = Output.Packet(self, message, group=Output.NARRATOR)
    p2.AddMessage(speech=text, letters=True)
    return p, p2

  OutNoSearchItem = OutNoSeekItem
  
  def OutStartSearch(self, message):
    '''
    Outputs a sound indicating searching has started.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, message)
    p.AddMessage(person=Output.SUMMARY, 
                 sound=Output.ISound(self).Action('search'))
    return p
  
  def OutEndSearch(self, message):
    '''
    Outputs a sound indicating a searching has ended. Says the name of the
    selected item by calling OutCurrentItem.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = self.OutCurrentItem(message)
    p.AddMessage(person=Output.SUMMARY, 
                 sound=Output.ISound(self).Action('search'))
    return p
    
  def OutDetailCurrent(self, message):
    '''
    Outputs one detail about the question and answer at a time.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = self.OutDetailCurrent_gen(message)
    if p is None:
      # play an end sound
      p = Output.Packet(self, message)
      p.AddMessage(sound=Output.ISound(self).State('last'),
                   person=Output.SUMMARY)
    return p
    
  def OutDetailCurrent_gen(self, message, *args, **kwargs):
    '''
    Virtual method. Generates one detail about the current context each time
    it is called.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass
  
  def OutChange(self, message):
    '''
    Virtual method. Placeholder for subclasses that need to respond to indirect 
    change notifications.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass
    
  def OutDeadLong(self, message):
    '''
    Virtual method. Reports information about a missing but active control.
    Gives an extended explanation of the missing control.

    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    pass
    
  def OutDeadShort(self, message):
    '''
    Plays a non-speech sound indicating the control is missing.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # the control is missing, inform the user
    p = Output.Packet(self, message)
    p.AddMessage(sound=Output.ISound(self).State('missing'), 
                 person=Output.SUMMARY)
    return p
  
  def OutNotImplemented(self, message, feature):
    '''
    Outputs a message saying that a feature is not available and sound 
    indicating the same.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param feature: Text describing the feature that is not available
    @type feature: string
    '''
    p = Output.Packet(self, message)
    p.AddMessage(speech=feature, sound=Output.ISound(self).Warn('refuse'), 
                 person=Output.SUMMARY)
    return p
