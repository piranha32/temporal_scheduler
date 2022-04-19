"""
Module shows how to use TemporalScheduler class to launch
single shot actions using functions using absolute and relative scheduled time.
"""

import time
from temporal_scheduler import TemporalScheduler


def function1():
    print("Function 1 called")

def function2():
    print("Function 2 called")

ts = TemporalScheduler()

# Schedule execution of function1 in 2 seconds using relative time
ts.schedule_task(function1, delta_t=2)

# Schedule execution of function2 in 3 seconds using absolute time
current_time = time.time()
ts.schedule_task(function2, absolute_time=current_time + 3)

# wait for 4 seconds
time.sleep(4)

# Shut down the scheduler
ts.shutdown()
