'''
py2exe compile script for Clique.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

from distutils.core import setup
import py2exe, glob, os

# win32com modifies __path__ at runtime and messes up modulefinder
# solution posted at http://starship.python.net/crew/theller/moin.cgi/WinShell
try:
  import modulefinder, sys
  import win32com
  for p in win32com.__path__[1:]:
    modulefinder.AddPackagePath("win32com", p)
  for extra in ["win32com.shell"]:
    __import__(extra)
    m = sys.modules[extra]
    for p in m.__path__[1:]:
      modulefinder.AddPackagePath(extra, p)
except ImportError:
  # no build path setup, no worries.
  pass

# build a list of all identity sounds
identity_sounds = []
for name in glob.glob('Output/sounds/identity/*'):
  if os.path.isdir(name):
    identity_sounds.append((name, glob.glob(os.path.join(name, '*.wav'))))

setup(name='Clique',
      version='0.3',
      author='Peter Parente',
      author_email='parente@cs.unc.edu',
      url='http://www.cs.unc.edu/~parente',
      description='Clique: Conversational audio display',
      options = {'py2exe': {'compressed': 1, 'optimize': 2,
                            'typelibs': [('{C866CA3A-32F7-11D2-9602-00C04F8EE628}', 0, 5, 0)]
                            }
                },
      console = [{'script': 'AUI.py', 'icon_resources': [(0, 'icon32.ico')]}],
      data_files=[('Output/sounds', glob.glob('Output/sounds/*.wav')),
                  ('Output/sounds/identity', glob.glob('Output/sounds/identity/*.wav')),
                  ('apps', glob.glob('apps/*.py'))]+identity_sounds
)
