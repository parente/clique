'''
Defines a manager and helper classes for maintaining associations between live
objects and sounds representing their identities.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

import weakref, os, random
import Constants
import Config

class IdentityGroup(object):
  '''
  Manages thematically related sounds used to represent tasks within a single
  program. Tries to assign each task a unique sound but reuses the available
  sounds if needed. Provides a method of getting the task sounds and the base
  program sound.

  @ivar base_sound: Filename of the base sound for the program mapped to this
      L{IdentityGroup}
  @type base_sound: string
  @ivar group_path: Path containing the sounds to be mapped to tasks
  @type group_path: string
  @ivar task_sound_map: Pairs task objects with identity sounds
  @type task_sound_map: weakref.WeakKeyDictionary
  @ivar all_groups: Set of sound filenames that can be used to represent related
      tasks within the program mapped to this group
  @type all_groups: set
  @ivar repeat: Running counter for reusing sounds
  @type repeat: integer
  '''
  def __init__(self, base_sound):
    '''
    Constructs paths pointing the base program identity sound and the folder
    storing the task sounds in this group. Builds a set of all available task
    identity sounds. Creates an empty dictionary to store task/sound mappings.
    '''
    group_name = base_sound.split(os.extsep)[0]
    self.base_sound = os.path.join(Constants.IDENTITY_FOLDER_NAME, base_sound)
    self.group_path = os.path.join(Constants.IDENTITY_FOLDER_NAME, group_name)
    self.task_sound_map = weakref.WeakKeyDictionary()
    group_path_rel = os.path.join(Constants.IDENTITY_SOUND_PATH,
                                  base_sound.split(os.extsep)[0])
    try:
      self.all_sounds = set([name for name in os.listdir(group_path_rel)
                             if os.path.isfile(os.path.join(group_path_rel, 
                             name))])
    except WindowsError:
      self.all_sounds = set()
    self.repeat = 0

  def GetBaseSound(self):
    '''
    Returns the base sound for the program.

    @return: Base sound
    @rtype: string
    '''
    return self.base_sound

  def GetLayerSound(self, source):
    '''
    Maps a task to a sound representing its identity.

    @param source: Task object
    @type source: L{View.Task.Base}
    @return: Filename for a sound representing the task
    @rtype: string
    '''
    # see if this source has already had a sound assigned
    try:
      return os.path.join(self.group_path, self.task_sound_map[source])
    except KeyError:
      pass
    # find sounds that are not in use
    sounds_in_use = self.task_sound_map.values()
    sounds_free = self.all_sounds - set(sounds_in_use)
    if len(sounds_free) > 0:
      # choose a random sound from those not in use
      sound = sounds_free.pop()
    else:
      # choose a random sound from those in use
      try:
        sound = sounds_in_use[self.repeat]
      except IndexError:
        # no layers available
        return None
      self.repeat = (self.repeat + 1) % len(self.all_sounds)
    self.task_sound_map[source] = sound
    return os.path.join(self.group_path, sound)

class IdentityManager(object):
  '''
  Manages sound groups for identifying program and task objects. Tries to assign
  a unique sound group to each program where a looping, ambient sound uniquely
  identifies the program across all running programs. Tries to assign
  thematically related sounds within a sound group to uniquely identify all
  tasks in a given program. Reuses sound groups and sounds within a group as
  needed.

  @ivar program_group_map: Pairs program types with L{IdentityGroup}s
  @type program_group_map: dictionary
  @ivar all_groups: Set of L{IdentityGroups} representing thematic groups
      of sounds that can be used to represent related tasks
  @type all_groups: set
  @ivar repeat: Running counter for reusing sounds
  @type repeat: integer
  '''
  def __init__(self):
    '''
    Builds a set of all available L{IdentityGroup}s. Creates an empty dictionary
    to store program/group mappings.
    '''
    identity_groups = {}
    # build a dictionary of identity groups keyed by their base sound names
    for fn in os.listdir(Constants.IDENTITY_SOUND_PATH):
      if os.path.isfile(os.path.join(Constants.IDENTITY_SOUND_PATH, fn)):
        ig = IdentityGroup(fn)
        identity_groups[ig.GetBaseSound()] = ig

    self.program_group_map = {}
    self.all_groups = set(identity_groups.values())
    self.repeat = 0

    # add permanent program mappings to the program group map
    for source, base_sound in Config.identity_history.items():
      self.program_group_map[source] = identity_groups[base_sound]

  def GetProgramIdentity(self, source):
    '''
    Maps a program to a sound representing its identity.

    @param source: Program object
    @type source: L{View.Task.Container.Program}
    @return: Filename for a sound representing the program
    @rtype: string
    '''
    source = source.Name
    # see if this source has already had a sound assigned
    try:
      return self.program_group_map[source].GetBaseSound()
    except KeyError:
      pass
    # find sounds that are not in use
    groups_in_use = self.program_group_map.values()
    groups_free = self.all_groups - set(groups_in_use)
    if len(groups_free) > 0:
      # choose a random sound from those not in use
      group = groups_free.pop()
    else:
      # choose one from the groups in use
      group = groups_in_use[self.repeat]
      self.repeat = (self.repeat + 1) % len(self.all_groups)
    self.program_group_map[source] = group
    # get the base sound
    bs = group.GetBaseSound()
    # add this permanent mapping to the user config
    Config.identity_history[source] = bs
    return bs

  def GetTaskIdentity(self, source):
    '''
    Maps a task to a sound representing its identity.

    @param source: Task object
    @type source: L{View.Task.Base}
    @return: Filename for a sound representing the task
    @rtype: string
    @raise KeyError: When the Task's container is not already assigned an
        identity group and so this Task cannot be mapped to a sound
    '''
    # determine which program owns this task
    container = source.GetContainer()
    # get the group for this container
    group = self.program_group_map[container.Name]
    # ask the group for an identity sound
    return group.GetLayerSound(source)

# make it a singleton
IdentityManager = IdentityManager()

if __name__ == '__main__':
  class program(object): pass
  objects = [program() for i in range(7)]
  class task(object):
    def __init__(self, i):
      self.i = i
    def GetContainer(self):
      return objects[self.i]
  tasks = [task(i/3) for i in range(21)]

  for o in objects:
    print IdentityManager.GetProgramIdentity(o)
  print '***'
  for o in objects:
    print IdentityManager.GetProgramIdentity(o)
  for t in tasks:
    print IdentityManager.GetTaskIdentity(t)
  print '***'
  for t in tasks:
    print IdentityManager.GetTaskIdentity(t)
