'''
Defines search related mixins.

@author: Peter Parente <parente@cs.unc.edu>
@copyright: Copyright (c) 2008 Peter Parente
@license: BSD License

All rights reserved. This program and the accompanying materials are made
available under the terms of The BSD License which accompanies this
distribution, and is available at
U{http://www.opensource.org/licenses/bsd-license.php}
'''

class CircularSearchMixin(object):
  '''
  Mixing providing a generic method using callbacks to perform a circular
  search through a body of items. How the search proceeds is entirely defined
  by the callbacks.
  '''
  def CircularSearch(self, start_cb, end_cb, move_cb, test_cb, found_cb,
                     reset_cb, text, current):
    '''
    Method for performing a generic, wrapping search over an entire collection.

    @param start_cb: Function to call when the search is starting
    @type start_cb: callable
    @param end_cb: Function to call when the search is ending
    @type end_cb: callable
    @param move_cb: Function to call to move to another item to test
    @type move_cb: callable
    @param test_cb: Function to call to test if an item contains the text
    @type test_cb: callable
    @param found_cb: Function to call when text is found in an item
    @type found_cb: callable
    @param reset_cb: Function to call when wrapping during search
    @type reset_cb: callable
    @param text: Text to locate
    @type text: string
    @param current: Start the search on the current item?
    @type current: boolean
    @return: True if wrapped, False if not wrapped, None if not found
    @rtype: boolean
    '''
    # set to first item to test
    curr = start_cb()
    try:
      if not current:
        curr = move_cb(start_cb())
    except (ValueError, AttributeError):
      # ignore any errors here, we might need to wrap
      pass
    else:
      while 1:
        if test_cb(curr, text):
          found_cb(curr)
          end_cb()
          return False
        # seek in desired direction
        try:
          curr = move_cb(curr)
        except ValueError:
          break
        except AttributeError:
          end_cb()
          return None
    try:
      # reset to endpoint
      curr = reset_cb(curr)
    except (ValueError, AttributeError):
      end_cb()
      return None
    while 1:
      if test_cb(curr, text):
        found_cb(curr)
        end_cb()
        return True
      # seek in desired direction
      try:
        curr = move_cb(curr)
      except (ValueError, AttributeError):
        break
    end_cb()
    return None
