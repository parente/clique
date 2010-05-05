'''
Defines global settings.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

# name of the user profile to use during this session
username = 'user'

# user settings
speech_rate = 3
master_volume = 200
say_on_focus = 'chunk' # say the current 'chunk', 'word', or nothing
# history of sounds paired with programs for consistency across runs
identity_history = {'speech exercises' : 'identity\\crickets.wav',
                    'workload questionnaires' : 'identity\\crickets.wav',
                    'usability questionnaires' : 'identity\\crickets.wav',
                    'volume control' : 'identity\\crickets.wav'}
log_file = 'results.txt'
log_data = []

# individual volume controls
content_voice = 255
content_sound = 150
narrator_voice = 200
narrator_sound = 150
summary_voice = 220
summary_sound = 150
related_voice = 180
related_sound = 140
unrelated_voice = 180
unrelated_sound = 140
change_sound = 150
looping_sound = 85
ambient_sound = 95
inter_sound = 50

# development settings
hook_mouse = False
speak_chars = True
speak_commands = False
# NOTE: no callbacks when using MS low quality voices
low_quality_voices = False
precache_voices = not low_quality_voices
catch_exceptions = True
debug = False
fast_shutdown = True
show_text = False
hold_threshold = 0.4

def log(text):
  log_data.append(text)

def save_log():
  f = file(log_file, 'w')
  f.write('\n'.join(log_data))
  f.close()

def load():
  import cPickle
  try:
    data = cPickle.load(file(username+'.config', 'rb'))
    globals().update(data)
  except (IOError, EOFError):
    pass

def save():
  import Config
  import cPickle
  d = {}
  d.update(vars(Config))
  keys = d.keys()
  for key in keys:
    if key.startswith('__'):
      del d[key]
  cPickle.dump(d, file(username+'.config', 'wb'))

# try to load previously stored profile
load()
