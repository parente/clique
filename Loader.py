'''
Provides access to the pattern descriptions stored on disk.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import os, os.path, imp, sys

ROOT = os.path.abspath('.\\apps')
# make sure the app path is in the import path
sys.path.append(ROOT)

class Stub(object):
  '''
  References an unloaded pattern description and provides a method to load it.

  @ivar library: Reference to the library of patterns
  @type library: L{Library}
  @ivar Name: Name of the program
  @type Name: string
  '''
  def __init__(self, library, name):
    '''
    Initialize an instance.

    See instance variables for parameter descriptions.
    '''
    self.library = library
    self.Name = name

  def __cmp__(self, other):
    '''
    Sorts stubs based on program names

    @param other: Stub to compare
    @type other: Stub
    '''
    if self.Name < other.Name:
      return -1
    elif self.Name == other.Name:
      return 0
    else:
      return 1

  def __call__(self):
    '''
    Loads the pattern description for the program with the given name.

    @return: Requested module
    @rtype: module
    '''
    # read that file to load the program description
    return self.library.LoadModuleByName(self.Name)

class Library(object):
  '''
  Manages the pattern descriptions stored on disk.

  @cvar root: Root path of where the pattern descriptions are stored
  @type root: string
  @ivar index: Module listing all of the supported applications
  @type index: module
  '''
  def __init__(self):
    '''
    Initializes the object by loading the index from disk.
    '''
    try:
      m = self.LoadModuleByFilename('index.py')
      self.index = m.index
    except IOError:
      self.index = {}

  def LoadModuleByName(self, name):
    '''
    Load the module with the given human readable name from disk.

    @param name: Human readable name of the module
    @type name: string
    @return: Requested module
    @rtype: module
    '''
    fn = self.index[name]
    return self.LoadModuleByFilename(fn)

  def LoadModuleByFilename(self, fn):
    '''
    Load the module with the specified filename from disk.

    @param fn: Filename of the requested module
    @type fn: string
    @return: Requested module
    @rtype: module
    '''
    fn = os.path.join(ROOT, fn)
    f = file(fn, 'r')
    i = fn.rfind('\\')
    name = fn[i+1:-3]
    m = imp.load_source(name, fn, f)
    f.close()
    return m

  def GetStubs(self):
    '''
    @return: Stubs for all patterned programs
    @rtype: list of L{Stub}
    '''
    return [Stub(self, k) for k in self.index.keys()]

Library = Library()
