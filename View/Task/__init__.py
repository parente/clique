'''
Defines organizational, task-level interaction patterns.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from Constants import *
from Base import Task as Base
from FormFill import FormFill
from LinkedBrowsing import LinkedBrowsing
from Wizard import Wizard
from DiskBrowsing import FileOpening, FolderBrowsing, FileSaving
from NoInteraction import RunAndReport, RunWaitReport
from Container import Program, ProgramManager
