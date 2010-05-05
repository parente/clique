'''
Defines classes for browsing for folders and files and saving files to disk.

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
import UIA, Output, Support, View, FormFill, Mixin
import win32file, win32api, os, string
import win32com.shell.shell as shell
import win32com.shell.shellcon as shellcon

# reference to important user folder
my_doc_path = shell.SHGetPathFromIDList(shell.SHGetSpecialFolderLocation
                                        (0, shellcon.CSIDL_PERSONAL)).lower()
my_doc_name = 'my documents'

# drive type names
drive_types = {win32file.DRIVE_CDROM: 'CD drive',
               win32file.DRIVE_FIXED: 'hard drive',
               win32file.DRIVE_RAMDISK: 'ram drive',
               win32file.DRIVE_REMOTE: 'network drive',
               win32file.DRIVE_REMOVABLE: 'removable drive'}

# characters not allowed in a file or folder name
invalid_chars = '\/:*?"<>|'

class FileSystem(Mixin.CircularSearchMixin):
  '''
  Tree model for the entire local filesystem. Uses a mixture of Python os 
  functions and Win32 specific functions.
  
  @cvar LastPath: Last folder visited
  @type LastPath: string
  @ivar cwd: Current folder being browsed
  @type cwd: string
  @ivar contents: Contents of the current folder
  @type contents: list
  @ivar curr: Index of the current selection in this folder
  @type curr: integer
  @ivar filter: Current filter settings
  @type filter: tuple
  @ivar exts: Current filter extensions
  @type exts: tuple
  @ivar search_anchor: Index of item selected at the start of a search
  @type search_anchor: integer
  '''
  advise(instancesProvide=[ITree, ISeekable, ISearchable, IInteractive,
                           IStrideable])
  LastPath = None
  
  def __init__(self):
    '''Initialize an instance.'''
    self.contents = []
    self.curr = 0
    self.search_anchor = 0
    self.filter = None
    self.Path = FileSystem.LastPath
    self.UpdateContents()

  def SetFilter(self, folders_only, *exts):
    '''
    Sets the filter for the filesystem listings to include folders only or 
    folders and files with the given extensions.
    
    @param folders_only: Only report folders?
    @type folders_only: boolean
    @param exts: Report files with these extensions (not including .) only
    @type exts: list
    '''
    self.exts = exts
    if folders_only:
      self.filter = ()
    elif len(exts):
      self.filter = self.exts
    else:
      self.filter = None
    self.UpdateContents()
    
  def GetContents(self, path, filter):
    '''
    Gets all the filtered contents of the given folder.
    
    @param path: Absolute path to the folder to list
    @type path: string
    @param filter: Filter the contents based on the given extensions
    @type filter: tuple
    @return: Contents of the given path
    @rtype: list
    '''
    # get the names of the files and folders in the current folder
    try:
      contents = os.listdir(path)
    except WindowsError:
      return []
    contents = [i.lower() for i in contents if 
                # we're at the root
                path is None or
                # we're not filtering
                filter is None or
                # the object is a folder
                os.path.isdir(os.path.join(path,i)) or
                # the object has one of the desired extensions
                reduce(lambda x,y: x|i.lower().endswith('.'+y), filter,
                       False)
                ]
    contents.sort()
    return contents
    
  def PrettyDriveName(self, drive):
    '''
    Build a human readable description of a drive name.
    
    @param drive: Drive path
    @type drive: string
    @return: Name of the drive
    @rtype: string
    '''
    kind = win32file.GetDriveType(drive)
    return '%s, %s' % (drive[0], drive_types.get(kind, 'drive'))
          
  def UpdateContents(self):
    '''
    Builds a list of the names of all the contents of a folder.

    @return: Filtered contents of the current folder
    @rtype: list
    '''
    if self.IsRoot():
      # get name and type of all drives
      self.contents = [drive for drive in
                       win32api.GetLogicalDriveStrings().split('\x00')[:-1]]
      self.contents.sort()
      # add shortcut to my documents
      self.contents.insert(0, my_doc_path)
    else:
      # filter the contents
      self.contents = self.GetContents(self.Path, self.filter)
    self.curr = 0
    return self.contents
    
  def Activate(self):
    '''
    Does nothing.
    
    @return: True, always ready for interaction
    @rtype: boolean
    '''
    return True
    
  def Deactivate(self):
    '''Does nothing.'''
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
    
  def GetParentName(self, default='root'):
    '''
    @param default: Name of the root
    @type default: string
    @return: Name of the current folder 
    @rtype: string
    '''
    if self.IsRoot():
      return default
    elif self.IsDocuments():
      return my_doc_name
    else:
      s = os.path.basename(self.Path)
      if s == '':
        # we're at the root of a drive
        return self.PrettyDriveName(self.Path)
      else:
        return s
    
  def GetSelectedName(self, default='No files or folders'):
    '''
    @param default: Text to announce when no item
    @type default: string
    @return: Name of the current selection
    @rtype: string
    '''
    if self.IsRoot():
      if self.curr > 0:
        # it's a drive, pretty up the name
        drive = self.contents[self.curr]
        return self.PrettyDriveName(drive)
      else:
        # it's the documents folder
        return my_doc_name
    elif self.GetItemCount() > 0:
      return self.contents[self.curr]
    else:
      return default
    
  def GetIndex(self):
    '''
    @return: Index of the current selection
    @rtype: integer
    '''
    return self.curr
    
  def GetItemCount(self):
    '''
    @return: Number of items in the current path
    @rtype: integer
    '''
    return len(self.contents)
  
  def GetChildCount(self):
    '''
    @return: Number of child items of the selected item
    @rtype: integer 
    '''
    try:
      if self.HasChildren():
        return len(self.GetContents(self.ChildPath, self.filter))
    except WindowsError:
      pass
    return 0
  
  def GetLevel(self):
    '''
    @return: Level of the current path, with the root being level one
    @rtype: integer
    '''
    path = self.Path
    if self.IsRoot():
      # the root is level 1
      return 1
    chunks = path.split('\\')
    if chunks[1] == '':
      # the root of a drive is level 2
      return 2
    elif path.startswith(my_doc_path):
      # the my doc folder is based off the root
      return len(chunks) - len(my_doc_path.split('\\')) + 2
    else:
      return len(chunks) + 1
    
  def HasChildren(self):
    '''
    @return: Is the current selection a folder, navigable, and contain children?
    @rtype: boolean
    '''
    if os.path.isdir(self.ChildPath):
      try:
        contents = os.listdir(self.ChildPath)
        return len(contents) > 0
      except WindowsError:
        return False
        
  def HasParent(self):
    '''
    @return: Is the parent not the root?
    @rtype: boolean
    '''
    return not self.IsRoot()
    
  def FirstItem(self):
    '''
    Sets the current path to the virtual root.
    
    @return: Did we navigate to the root?
    @rtype: boolean
    '''
    self.Path = None
    return True
    
  def NextLevel(self):
    '''
    Sets the current path to a child of the current element, if that child is
    navigable.
    
    @return: Is the child navigable?
    @rtype: boolean
    '''
    if self.GetItemCount() < 1:
      return False
    folder = self.contents[self.curr]
    if not self.HasChildren():
      return False
    elif self.IsRoot():
      self.Path = folder
    else:
      self.Path = os.path.join(self.Path, folder) 
    return True
    
  def PrevLevel(self):
    '''
    Sets the current path to the parent of the current item, if the current
    path is not the root.
    
    @return: Is the parent navigable?
    @rtype: boolean
    '''
    if self.IsRoot():
      # don't go anywhere
      return False
    elif self.IsDocuments():
      # move from documents folder directly to root
      self.Path = None
      return True
    else:
      base, curr = os.path.split(self.Path)
      if curr == '':
        # we're at the root of a drive, go to the root node
        self.Path = None
        curr = base
      else:
        self.Path = base
      # set selection to the previous parent name
      self.curr = self.contents.index(curr)
      return True
    
  def NextItem(self):
    '''
    Selects the next child item.
    
    @return: Did selection wrap?
    @rtype: boolean
    '''
    c = self.curr
    if self.GetItemCount() > 0:
      self.curr = (self.curr + 1) % self.GetItemCount()
    return self.curr < c
    
  def PrevItem(self):
    '''
    Selects the previous child item.
    
    @return: Did selection wrap?
    @rtype: boolean
    '''
    c = self.curr
    if self.GetItemCount() > 0:
      self.curr = (self.curr - 1) % self.GetItemCount()
    return self.curr > c

  def _SearchStart(self):
    '''
    Callback for L{CircularSearch}. Gets the selected item.
    
    @return: Index of the selected item
    @rtype: integer
    '''
    return self.curr
  
  def _SearchEnd(self):
    '''
    Callback for L{CircularSearch}. Does nothing.
    '''
    pass
  
  def _SearchAhead(self, curr):
    '''
    Callback for L{CircularSearch}.
    
    @param curr: Index of the current item to test
    @type curr: integer
    @return: Index of next item to test
    @rtype: integer
    @raise ValueError: When no more items to test in current direction
    '''
    curr += 1
    if curr >= self.GetItemCount():
      raise ValueError
    return curr
  
  def _SearchBehind(self, curr):
    '''
    Callback for L{CircularSearch}.
    
    @param curr: Index of the current item to test
    @type curr: integer
    @return: Index of next item to test
    @rtype: integer
    @raise ValueError: When no more items to test in current direction
    '''
    curr -= 1
    if curr < 0:
      raise ValueError
    return curr
  
  def _SearchFirst(self, curr):
    '''
    Callback for L{CircularSearch}.
    
    @param curr: Index of the current item to test
    @type curr: integer
    @return: Index of the first item
    @rtype: integer
    '''
    return 0
  
  def _SearchLast(self, curr):
    '''
    Callback for L{CircularSearch}.
    
    @param curr: Index of the current item to test
    @type curr: integer
    @return: Index of the last item
    @rtype: integer
    '''
    return self.GetItemCount()-1
  
  def _SearchSelectAhead(self, curr):
    '''
    Callback for L{CircularSearch}. Selects the current item.
    
    @param curr: Index of the current item to test
    @type curr: integer
    '''
    self.curr = curr
    
  def _SearchSelectBehind(self, curr):
    '''
    Callback for L{CircularSearch}. Selects the current item.
    
    @param curr: Index of the current item to test
    @type curr: integer
    '''
    self.curr = curr
  
  def _SearchTestStartsWith(self, curr, text):
    '''
    Callback for L{CircularSearch}. Checks if the current item starts with the
    given text.
    
    @param curr: Index of the current item to test
    @type curr: integer
    @param text: Search string
    @type text: string
    @return: The current item starts with the given text?
    @rtype: boolean
    '''
    if self.contents[curr] == my_doc_path:
      return my_doc_name.startswith(text.lower())
    else:
      return self.contents[curr].lower().startswith(text.lower())       
  
  def _SearchTestAll(self, curr, text):
    '''
    Callback for L{CircularSearch}. Checks if the current item contains all of
    the given text.
    
    @param curr: Index of the current item to test
    @type curr: integer
    @param text: Search string
    @type text: string
    @return: The current item contains the given text?
    @rtype: boolean
    '''
    if self.contents[curr] == my_doc_path:
      name = my_doc_name.lower()
    elif self.IsRoot():
      name = self.PrettyDriveName(self.contents[curr]).lower()
    else:
      name = self.contents[curr].lower()
    return name.find(text.lower()) > -1
  
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
    self.search_anchor = self.curr
    
  def SearchReset(self):
    '''
    Resets the current item to the one that was selected when the search began.
    '''
    self.curr = self.search_anchor
      
  def GetChildPath(self):
    '''
    @return: Absolute path of the selected child item
    @rtype: string
    '''
    if self.IsRoot():
      return self.contents[self.curr]
    elif self.GetItemCount() > 0:
      return os.path.join(self.Path, self.contents[self.curr])
    else:
      return '...'
  ChildPath = property(GetChildPath)
  
  def GetPath(self):
    '''
    @return: Current path
    @rtype: string
    '''
    return self.cwd

  def SetPath(self, path):
    '''
    @param path: Current path
    @type path: string
    '''
    self.cwd = path
    self.UpdateContents()
  Path = property(GetPath, SetPath)
  
  def IsDocuments(self):
    '''
    @return: Is the current path the documents folder? 
    @rtype: boolean
    '''
    return self.Path == my_doc_path

  def IsRoot(self):
    '''
    @return: Is the current path the root of the file system?
    @rtype: boolean
    '''
    return self.Path is None
    
  def IsChildFile(self):
    '''
    @return: Is the current selection a file?
    @rtype: boolean
    '''
    return os.path.isfile(self.ChildPath)
    
  def IsChildFolder(self):
    '''
    @return: Is the current selection a folder and navigable?
    @rtype: boolean
    '''
    if os.path.isdir(self.ChildPath):
      try:
        os.listdir(self.ChildPath)
        return True
      except WindowsError:
        return False
        
  def IsClash(self, name):
    '''
    Checks if the given filename will clash with another file in this folder.
    If the name has no extension, considers all extensions stated in the filter
    extensions. If the name has an extension, it only considers that filename.
    
    @param name: Filename without path
    @type name: string
    @return: Does the filename clash with an existing file?
    @rtype: boolean
    '''
    name = name.lower()
    has_ext = len([e for e in self.exts if name.endswith('.'+e)])
    contents = self.GetContents(self.ChildPath, None)
    if has_ext:
      # the filename has an extension, check the full name
      for f in contents:
        if os.path.isfile(os.path.join(self.ChildPath, f)) and f==name:
          return True
      return False
    else:
      # the filename has no extension, check if the given name plus the known
      # extensions clashes with any existing files
      for f in contents:
        if os.path.isfile(os.path.join(self.ChildPath, f)):
          for e in self.exts:
            if ('%s.%s' % (name,e)) == f:
              return True
      return False
  
  def IsValidName(self, name):
    '''
    Checks if the give filename is a valid name.
    
    @param name: Filename to check
    @type name: string
    @return: Is the filename valid?
    @rtype: boolean
    '''
    has_word_char = False
    for c in name:
      has_word_char = c in string.printable
      if c in invalid_chars: return False
    return has_word_char
   
class FileNameTextEntry(View.Control.TextEntry):
  '''
  Text entry for a filename. Checks for clashes between this filename and an
  existing file.
  
  @ivar fs: Filesystem model used to check for clashes
  @type fs: L{FileSystem}
  '''
  def __init__(self, parent, model, filesystem, **kwargs):
    super(FileNameTextEntry, self).__init__(parent, model, **kwargs)
    self.fs = filesystem
    # notify ourself of any changes
    self.AddChangeListener(self)
  
  def OnIndirectChange(self, message):
    '''
    Tests if the text in the filename field clashes with a filename in the 
    current directory.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''    
    text = IText(self.model).GetAllText()
    if self.fs.IsClash(text):
      p = self.OutFilenameClash(message, text)
      self.Output(self, p)
      
  def OutFilenameClash(self, message, fn):
    '''
    Outputs a sound indicating the current filename clashes with an existing 
    file.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    @param fn: Clashing filename
    @type fn: string
    @return: Output to be played
    @rtype: L{Output.Messages.OutboundPacket}
    '''
    p = Output.Packet(self, None)
    p.AddMessage(sound=Output.ISound(self).Warn('clash'), person=Output.SUMMARY,
                 speech='A file with name %s already exists.' % fn)
    return p
  
class FolderBrowsing(FormFill.FormFill):
  '''
  Browse the file system for a folder.

  @cvar filename_path: Path pointing to the file or folder name text box
  @type filename_path: string
  @cvar SIMPLE_FILENAME_PATH: Constant aapath for standard file dialogs
  @type SIMPLE_FILENAME_PATH: string
  @cvar EXTENDED_FILENAME_PATH: Constant aapath for extended file dialogs
  @type EXTENDED_FILENAME_PATH: string
  @ivar fs: Reference to the file system model
  @type fs: L{FileSystem}
  '''
  Name = 'choose a folder'
  filename_path = None
  SIMPLE_FILENAME_PATH = '/dialog[3]/window[7]/editable text[3]'
  EXTENDED_FILENAME_PATH = '/dialog[3]/window[8]/client[3]/window[0]/combo box[3]/window[0]/editable text[3]'
  
  def __init__(self, parent, model):
    '''Initializes an instance.'''
    super(FolderBrowsing, self).__init__(parent, model)
    self.fs = FileSystem()
    self.fs.SetFilter(True)
    self.AddField(View.Control.Tree(self, self.fs, name='folders'))
    self.text_model = UIA.Adapters.OverwritableTextBox(self,
                                                       self.filename_path,
                                                       reset=True, clear=True)

  def BuildPath(self, current):
    '''
    Builds the final pathname to be inserted into the filename text box when
    the task is about to complete.
    
    @param current: Path to the currently selected file
    @type current: string
    @return: Absolute name to be used to choose a file or folder
    @rtype: string
    '''
    return current
    
  def IsValid(self):
    '''
    @return: None if the selected item is a valid choice for completion, else
      an error string for the user
    @rtype: None or string
    '''
    if self.fs.IsChildFolder():
      return None
    else:
      return 'Select a valid folder or drive.'
  
  def OnReadyToComplete(self, message):
    '''
    Stores the last folder visited and inserts the full path to the selected
    object returned by L{BuildPath}. Calls the parent class version of this
    method to run the completion macro.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # get the full path and put it into the file textbox
    self.text_model.Activate()
    self.text_model.SetText(self.BuildPath(self.fs.ChildPath))
    # store the last browsed path
    FileSystem.LastPath = self.fs.Path
    super(FolderBrowsing, self).OnReadyToComplete(message)

  def OnEscape(self, message):
    '''
    Cancels the folder browser.
    
    @param message: Message that caused this event handler to fire
    @type message: L{Input.Messages.InboundMessage}
    '''
    # store the last browsed path
    FileSystem.LastPath = self.fs.Path
    super(FolderBrowsing, self).OnEscape(message)
    
class FileOpening(FolderBrowsing):
  '''Browse the file system for a file to open.'''
  Name = 'choose a file'
  
  def __init__(self, parent, model):
    '''Initializes an instance.'''
    super(FileOpening, self).__init__(parent, model)
    self.fs.SetFilter(False)
    self.fields[0].Name = 'files and folders'
    
  def FilterByExtension(self, *exts):
    '''
    Sets the extension filter. Files not having one of the given extensions will
    not be shown.
    
    @param exts: Allowed extensions
    @type exts: tuple
    '''
    self.fs.SetFilter(False, *exts)

  def IsValid(self):
    '''
    @return: None if the selected item is a valid choice for completion, else
      an error string for the user
    @rtype: string or None
    '''
    if self.fs.IsChildFile():
      return None
    else:
      return 'Select a valid file.'

class FileSaving(FolderBrowsing):
  '''
  Browse the file system for a folder in which to save a file and enter a 
  new filename for that file.
  '''
  Name = 'choose a folder and give the file a name'
  
  def __init__(self, parent, model):
    '''Initializes an instance.'''
    super(FileSaving, self).__init__(parent, model)
    self.AddField(FileNameTextEntry(self, self.text_model, self.fs, 
                                    name='filename'))
    # let the filename entry listen for changes in the filesystem tree
    self.fields[0].AddChangeListener(self.fields[1])
    
  def FilterByExtension(self, *exts):
    '''
    Sets the extension filter. The extensions will be used to test potential 
    name clashes. Only folders are shown during saving.
    
    @param exts: Allowed extensions
    @type exts: tuple
    '''
    self.fs.SetFilter(True, *exts)

  def IsValid(self):
    '''
    @return: None if the selected item is a valid choice for completion, else
      an error string for the user
    @rtype: None or string
    '''
    if self.fs.IsValidName(self.text_model.GetAllText()):
      return None
    else:
      return 'Enter a valid filename.'
  
  def BuildPath(self, current):
    '''
    Builds the final pathname to be inserted into the filename text box when
    the task is about to complete.
    
    @param current: Path to the currently selected file
    @type current: string
    @return: Absolute name to be used to choose a file or folder
    @rtype: string
    '''
    return os.path.join(current, self.text_model.GetAllText())
  
if __name__ == '__main__':
  pass
