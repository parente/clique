'''
Startup file for the Clique system.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''
import Config
import UIA
import System
import Input
import Output
import View
import Output.Sound

if __name__ == '__main__':
  try:
    import psyco
    psyco.full()
  except ImportError:
    print 'psyco not found'

  # create input, output, and program managers
  im = Input.Manager()
  om = Output.Manager(im)
  # order is important here because first instance of pump must have input manager
  p = System.Pump(im)
  pm = View.Task.ProgramManager(om)
  p.Start()
  # save user config
  Config.save()
