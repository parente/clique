'''
Defines constants for positioning speakers, assigning speaker voices, adding
internal output message constants, and defining other constants used by the
output system.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import string, math, os
import Input, Config

def TimeToSpeak(words):
  '''
  Computes an estimate of the amount of time required to speak the given number
  of words based on the current speech rate.
  
  @param words: Number of words
  @type words: integer
  @return: Time to speak the words in minutes
  @rtype: float
  '''
  # values computed using Mike16 on two bodies of 200 words each
  # function is more like an exponential, this linear version overestimates
  return words/(20.42*Config.speech_rate+113.85)

# constants for speaker positions
CENTER = (0,0,-1)
CENTER_OFFSET = (1*math.cos(87*math.pi/180),0,-1)
FRONT_RIGHT = (1*math.cos(80*math.pi/180), 0, 1*math.sin(80*math.pi/180))
FRONT_RIGHT_OFFSET = (1*math.cos(77*math.pi/180), 0, 1*math.sin(77*math.pi/180))
FRONT_LEFT = (1*math.cos(100*math.pi/180), 0, 1*math.sin(100*math.pi/180))
FRONT_LEFT_OFFSET = (1*math.cos(103*math.pi/180), 0,1*math.sin(103*math.pi/180))
LEFT = (1*math.cos(150*math.pi/180),0,1*math.sin(150*math.pi/180))
LEFT_OFFSET = (1*math.cos(153*math.pi/180),0, 1*math.sin(153*math.pi/180))
RIGHT = (1*math.cos(30*math.pi/180),0, 1*math.sin(30*math.pi/180))
RIGHT_OFFSET = (1*math.cos(27*math.pi/180),0, 1*math.sin(27*math.pi/180))

# constants for voices
CONTENT_VOICE = 'ATT-DT-14-Mike16'
SUMMARY_VOICE = 'ATT-DT-14-Crystal16'
RELATED_VOICE = 'ATT-DT-14-Mel16'
OUTSIDE_VOICE = 'ATT-DT-14-Mel16'
NARRATOR_VOICE = 'ATT-DT-14-Julia16'
if Config.low_quality_voices:
  CONTENT_VOICE, SUMMARY_VOICE, RELATED_VOICE, OUTSIDE_VOICE, NARRATOR_VOICE = ['MSSam']*5
CACHE_VOICES = [NARRATOR_VOICE, CONTENT_VOICE, SUMMARY_VOICE, RELATED_VOICE, OUTSIDE_VOICE]

# internal output messages
SAY_WORD = Input.Constants.GenCommandID()
SAY_SENTENCE = Input.Constants.GenCommandID()
SAY_DONE = Input.Constants.GenCommandID()
PACKET_START = Input.Constants.GenCommandID()
PACKET_DONE = Input.Constants.GenCommandID()
PACKET_PREEMPT = Input.Constants.GenCommandID()
MEMORY_INSERT = Input.Constants.GenCommandID()

# add mappings from output messages to methods
cmd_dispatch = {SAY_WORD: 'OnSayWord',
                SAY_SENTENCE: 'OnSaySentence',
                SAY_DONE: 'OnSayDone',
                PACKET_START: 'OnPacketStart',
                PACKET_DONE: 'OnPacketDone',
                PACKET_PREEMPT: 'OnPacketPreempt',
                MEMORY_INSERT : 'OnMemoryInsert'
              }
Input.Constants.AddDispatch(cmd_dispatch)
                
# characters that need to be replaced with text to be spoken properly
CHARACTER_MAP = {'-' : 'dash', '^' : 'caret', '<' : 'less than', 
                 '>' : 'greater than', '.' : 'dot', ',' : 'comma', 
                 '?' : 'question mark', '!' : 'exclamation point', 
                 '(' : 'left parenthesis', ')' : 'right parenthesis', 
                 '{' : 'left brace', '}' : 'right brace', '[' : 'left bracket', 
                 ']' : 'right bracket', '_' : 'underscore', ':' : 'colon', 
                 ';' : 'semicolon', '~' : 'tilde', ' ' : 'space', 
                 '\n' : 'new line', "'" : 'apostrophe', 
                 '"' : 'quote', '`' : 'grav'}

# constants defining groups of speakers
CONTEXT = 0
ACTIVE_CTRL = 1
ACTIVE_PROG = 2
INACTIVE_PROG = 3
NARRATOR = 4

# constants representing speakers
CONTENT = 0
SUMMARY = 1
CHANGE = 0
AMBIENCE = 1
LOOPING = 2
INTERMITTENT = 3

# size of the output history
HISTORY_SIZE = 50

# bookmark type constants
BM_SOUND = 0
BM_SPEECH = 1

# path to sounds
SOUND_PATH = os.path.join('Output', 'sounds')
IDENTITY_FOLDER_NAME = 'identity'
IDENTITY_SOUND_PATH = os.path.join(SOUND_PATH, IDENTITY_FOLDER_NAME) 

# spin delay for all worker threads
SPIN_DELAY = 0.01

# spelling constants
SPELL_FILTER = string.punctuation+string.whitespace
