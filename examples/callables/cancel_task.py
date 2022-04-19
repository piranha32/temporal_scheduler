import time
from temporal_scheduler import TemporalScheduler

def function1(task_state):
    """
    When called, function will print a message and increase by one
    value of "counter" field in the dict task_state
    """
    print("Function 1 called")
    task_state["counter"] += 1


ts = TemporalScheduler()

# state variable for the function
# Value of the counter is initialized to 0. It is increased by one on each
# call to function1.
# After the first timer fires, the counter value will be 1.
# After the second call the value should be 2, but if canceling
# the timer succeeds, counter value should remain at 1.
#
state = {"counter": 0}

# Schedule execution of function1 in 2 seconds using relative time
print("Scheduling first execution of the function")
ts.schedule_task(function1, delta_t=2, task_args=(state,))

time.sleep(3)
print("\nCounter value should be 1")
print("Counter: %s" % state["counter"])

# Schedule execution of function1 in 3 seconds
print("Scheduling second execution of the function")
t_id = ts.schedule_task(function1, delta_t=3, task_args=(state,))

# cancel the task 1 second before the timer fires
time.sleep(2)
ts.cancel_task(t_id)

# After 2 seconds the counter value should still be 1
print("\nCounter value will be 1 if the function executed, and 1 if the timer was successfully cancelled.")
print("Counter: %s" % state["counter"])

ts.shutdown()

