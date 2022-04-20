# TemporalScheduler

Lightweight temporal scheduler for thread synchronization and code execution

The package implements a lightweight and simple to use temporal scheduler for callable 
tasks (functions) and events. It started as a part of my project, but over time I found it
useful enough to turn the code into a standalone package.

Callable actions are executed in own threads, so an exception during execution will 
not interfere with operation of the scheduler.

# Installation

```pip install temporal_scheduler ```

# Usage

Please see [examples](examples/) directory

# Requirements

Package depends on ```SortedDict```


# License

GPLv3



# Theory of operation

## Timing
The scheduler relies on ```threading.Event``` for precise timing. When the next task for execution
arrives, the event enters wait with timeout set to the interval between the current time and 
the execution time.
If no tasks are scheduled for execution, the event enters a wait with no timeout.

If scheduling a new arriving task requires modification of the current head task 
(to be executed next), e.g. when a task arrives to an empty queue, requested 
execution time is earlier than the current head task, or the head list becomes empty, 
the head task is adjusted, and the event is triggered. 

If the event is triggered by a timeout, the worker thread processes the head task list.
For each callable task on the list a new execution thread is executed and started.\
For event tasks the event is triggered.

When the event is triggered, the head task list is already populated by the scheduling
method, and the working thread doesn't need to take any action. The new timeout is 
computed, and the thread enters sleep.

## Task scheduling

The scheduler maintains two lists of tasks:
- **Tasks ready for execution** is a list of tasks which will be executed when the scheduler 
thread wakes up.
- **Task queue** is a set of tasks with execution times following 
the execution time of the take on the "ready" list.

The task queue is organized as a *sorted dictionary*. The data structure behaves as 
a regular dictionary in the sense that it can be treated as a key-value store, 
and a sorted list, where the keys have defined order.\
With timestamps used as key values, it allows to easily organize and manage the 
scheduled tasks.\
Because more than task can be scheduled for execution with the same timestamp, 
each entry in the queue is organized as a list. 


Most of the scheduling work is performed by the ```schedule_event``` method of the internal class
```TemporalScheduler.TimerThread``` class. The ```TimerThread.schedule_task``` method
is just a wrapper, which performs sanity checks and input data normalization.\
In ```schedule_event``` the incoming request is processed using the following decision tree:

```
|
| time is in the past
+--------------------------------------------------------- (1).
|
| Nothing on the scheduler list
| self.current_time is None
+--------------------------------------------------------- (2).
|
| self.current_time > time
| (event earlier than currently scheduled)
+--------------------------------------------------------- (3).
|
| time not in self.events (new time point)
+--------------------------------------------------------- (4).
|
|                              callback on the list
| time == self.current_time  +---------------------------- (5).
| upcoming execution time    |
+----------------------------+
|                            | callback not on the list
|                            +---------------------------- (6).
|
|                              callback on the list
|                            +---------------------------- (7)
| time in self.events        |
+----------------------------+
|                            | callback not on the list
|                            +---------------------------- (8)
|
```


- **Case 1: time is in the past**\
    This case is handled by the wrapper method.
    The call fails with ```ValueError``` exception.

- **Case 2: Nothing on the scheduler list, self.current_time is None**
    In this case the task is immediately added to the list of tasks ready for execution, 
    and the scheduler thread is woken up to schedule execution.\
    New task ID is returned.

- **Case 3: The event is earlier than currently scheduled**
    The tasks from list of tasks ready for execution are moved back to the queue,
    the arriving task is placed on the ready list, and the scheduler thread is woken up to
    adjust its schedule.\
    New task ID is returned.

- **Case 4: time not in ```self.events``` (new time point)**
    The arriving task is not ready for placement on the execution list and is added to the scheduler queue.
    In the queue is no entry for its execution time, and new entry is created.\
    New task ID is returned.

- **Case 5: Arriving task is a duplicate of a task on the list of tasks ready for execution**
    Arriving task is a duplicate of an existing entry of a task on the execution list.\
    The ID of the task in the system is returned.

- **Case 6: Arriving task is not a duplicate and ready for execution**
    Arriving task is not a duplicate. The task is added to the execution list.
    There is no need to wake up the scheduler thread.\
    New task ID is returned.

- **Case 7: Arriving task has timestamp already present in the scheduler queue, and is a duplicate**
    Arriving task is a duplicate of an existing entry of a task in the scheduler queue.\
    The ID of the task in the system is returned.

- **Case 8: Arriving task has timestamp already present in the scheduler queue, and is not a duplicate**
    The timestamp of the arriving task is already in the queue, but it's not a duplicate.
    The task is added to the list of tasks associated with this timestamp.
    New task ID is returned.

## Detecting duplicates
The comparison of tasks takes into account the timestamp, callable, and the arguments.\
Comparison of tuples (for positional args) and dictionaries (for names args) is used to determine if the sets identical.
No deep comparison is performed. The task is determined a duplicate if all 4 comparisons return positive results.

## Periodic tasks
Periodic takes are implemented by re-scheduling them at the execution time.
When the scheduler thread processes a task with ```periodic``` flag set, the task is resubmitted to the scheduler.
The execution time is calculated by using the adding the task period to the current execution time.\
The new task is scheduled with the same task ID as the currently executing task.
Otherwise, it would be impossible to cancel a periodic task after first execution.

## Processing of ```threading.Event``` tasks
The ```Event``` class of tasks has been introduced as an optimized method of synchronizing threads.
A task can be a function, which triggers an event. However, this is a very simple situation, and creating a new worker 
thread and calling a callback function would be extremely wasteful. 
This becomes very important when the events are triggered with high frequency.



# Author


`TemporalScheduler` was written by `Jacek Radzikowski <jacek.radzikowski@gmail.com>`.
