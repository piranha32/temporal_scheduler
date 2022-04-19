"""
Module shows how to use TemporalScheduler class to launch
periodic actions.

The task is scheduled with 1 second periodd, and cancelled after 5 seconds.
"""

import time
from temporal_scheduler import TemporalScheduler


def function1():
    print("Function 1 called")

ts = TemporalScheduler()

# Execute action once a second
# Task ID must be saved for task cancellation.
print("Scheduling the task")
action_id = ts.schedule_task(function1, period=1)

time.sleep(5)
print("Cancelling the task")
ts.cancel_task(action_id)

ts.shutdown()
