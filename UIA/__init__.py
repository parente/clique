'''
Defines objects for managing communication between Clique and an underlying GUI.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import pyAA
import Mixin

# add the StabilityMixin to the AccessibleObject class
modifiers = ['DoDefaultAction', 'Select', 'SetFocus', 'SendKeys']
init = ['__init__']
unsafe = ['ChildFromPath', 'FindOneChild', 'FindAllChildren', 'GetChildren']
mix = Mixin.StabilityMixin(pyAA.AccessibleObject)
mix.StirInto(include=['SendKeys'])
mix.WrapMethods(mix.CheckWrapper, include=unsafe)
mix.WrapMethods(mix.DisturbWrapper, include=modifiers)
mix.WrapMethods(mix.InitializeWrapper, include=init)
mix.StirInto(exclude=['SendKeys'])

from Macro import *
from Watcher import *
import Adapters
from pyAA import Constants
