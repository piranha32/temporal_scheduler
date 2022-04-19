"""
Module shows how to use pass arguments to the function
"""

import time
from temporal_scheduler import TemporalScheduler


def function1(x, y, z):
    print("Function 1 called with arguments: x=%s, y=%s, z=%s" % (x, y, z))

ts = TemporalScheduler()

# Execute the function with 1 second delay
#
# Value of argument x is passed as positional argument.
# Values of positional arguments are passed as a tuple.
#
# Values of arguments y, and z are passed as named arguments.
# Values of named arguments are passed as a dict.
action_id = ts.schedule_task(function1, delta_t=1, task_args=(1,), task_kwargs={'y':2, 'z':3})

time.sleep(2)
ts.shutdown()
