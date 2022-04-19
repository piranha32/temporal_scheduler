"""
Implement lightweight temporal action scheduler.

The module implements a temporal scheduler, which can
execute actions at specified moments.
# The execution time can be specified as relative time
(e.g. in 5 seconds), or absolute time (e.g. execute
action on 2022-04-09 18:42:00)

The actions can be executed once, or periodically.

Two action types are available: functions and events.

Function action executes a function passed as the argument.
The function will be executed in a separate thread.
Additional named and positional arguments can be
passed to the function at the time of scheduling.

Event actions set an event. This type of action has been
added to avoid creating new threads for a simple synchronization
of running threads.

"""

# pylint: disable=consider-using-f-string, invalid-name, consider-using-dict-items, wrong-import-position
from threading import Thread, Event, Lock
import time
from sortedcontainers import SortedDict


class IDServer:
    """Implements a thread-safe service generating unique ID numbers.

    An instance of this class generates unique ID numbers for the sake of 
    identifying objects within a closed context. The numbers do not need to 
    be globally unique, do not need to be cryptographically secure.
    The important thing is that they are unique across all threads which
    share the generator.
    Simple sequential number generator works fine.

    Arguments:
        start_id - starting ID number. Defaults to 0.

    Attributes:
        id - current value of the ID counter
        id_mutex - mutex protecting access to the ID attribute
    """

    def __init__(self, start_id=0):
        """constructor for IDServer"""
        self.id = start_id
        self.id_mutex = Lock()

    def get_id(self):
        """
        Return a unique identifier.

        The number is unique for all threads sharing the server.

        Returns:
            Unique ID value
        """
        self.id_mutex.acquire()
        uid = self.id
        self.id += 1
        self.id_mutex.release()
        return uid


class TemporalScheduler:
    """
    Class impelements a temporal execution scheduler.

    The objects executed by the scheduler can be either functions, or events.
    If a function is passed as the argument of the timer, it will be executed
    in a separate thread.

    For temporal synchronization purposes of multiple threads, an event object
    can be passed as the argument. This eliminates the need to spawn a new thread
    and execute code only to send a synchronization event.
    """

    class TimerThread(Thread):
        """
        The class impelements timer executor functionality.

        I need to use Thread object to execute the thread.
        If I just use a function, I will have no way to self-remove
        from the executors list.
        """

        class TimerExecutor(Thread):
            """
            The class impelements timer executor functionality.

            This is an internal timer class, not intended for general use.
            """

            def __init__(self,
                         callback,
                         executors, executors_mutex,
                         task_args,
                         task_kwargs):
                """
                Initializes the timer executor object.

                Arguments:
                    callbask -
                    executors -
                    executors_mutex -
                    task_args -
                    task_kwargs -
                """

                Thread.__init__(self)
                self.callback = callback
                self.executors = executors
                self.executors_mutex = executors_mutex
                self.task_args = task_args
                self.task_kwargs = task_kwargs

            def run(self):
                """
                Function executes the scheduler action.

                Function executes the callback function, and after completing
                execution removes itself from the list of executors in the
                scheduler object.
                """

                self.callback(*self.task_args, **self.task_kwargs)
                try:
                    self.executors_mutex.acquire()
                    self.executors.remove(self)
                finally:
                    self.executors_mutex.release()

        def __init__(self):
            """
            Method initializes the TimerThread object.

            """
            Thread.__init__(self)
            self.timer_event = Event()

            # sorted dict for keeping the queue of wake-up events
            self.events = SortedDict()

            # description of pending event (next to execute)
            self.current_time = None

            # list of actions to execute for current execution time stamp
            self.current_event_actions = []

            # Mutex protecting access to current execution attributes
            self.current_mutex = Lock()

            # Timer exits the execution loop when self.running is set to False
            self.running = True

            # List of active task executors
            self.executors = []

            # Mutext protecting access to self.executors
            self.executors_mutex = Lock()

            # Provides new task ID when scheduling a new task
            # self.task_id = id_server.IDServer()
            self.task_id = IDServer()
            # self.verbose = False

            # "don't wait" threshold - execute immediately if current
            # and scheduled times are close.
            self.dontwait_threshold = 0.01

        def schedule_event(self,
                            action,
                            requested_time=None, period=None,
                            comment=None,
                            rid=None,
                            task_args=None, task_kwargs=None,
                            last_execution=None):
            """
            Schedule execution of a task.

            Method schedules execution of a task. The task can be either
            one-time, executed at the specified moment (absolute time),
            or periodic, executed every 'period' seconds.
            First execution of a periodic task will occur at
            now + period (no immediate execution).

            On successfull scheduling method returns scheduled task id. The id can be used
            to cancel the task.

            Arguments:
                action - threading.Event or callback to call when event is due
                requested_time - absolute execution time for one-time events
                period - period for periodic events.
                comment - comment for the task. Not used at the moment
                rid - id to assign to the task. Used internally to
                        re-schedule periodic tasks.
                task_args - positional arguments for the executed task.
                task_kwargs - named arguments for the executed task.
                last_execution - time of the previous execution for periodic
                                 tasks. For reporting purposes only.

            Returns:
                None - if task is expired at the moment of scheduling
                        (execution time is in the past)
                task ID - for successfully scheduled tasks.
            Decision tree:
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
            |
            |
            |                              callback on the list
            |                            +---------------------------- (7)
            | time in self.events        |
            +----------------------------+
            |                            | callback not on the list
            |                            +---------------------------- (8)
            |

            """


            scheduled_time = requested_time
            # For periodic tasks requested time is the time of the first execution.
            # If a task is periodic and no first execution time is provided, assume that
            # the first execution will be after period time from now.
            if period is not None and scheduled_time is None:
                scheduled_time = time.time() + period

            # scheduled time in the past
            # case (1)
            #
            # Case handled by upstream method (TemporalScheduler.schedule_event())
            # if scheduled_time < time.time():
            #     ValueError("%% Need time machine. Send money")

            if task_args is None:
                task_args = ()
            if task_kwargs is None:
                task_kwargs = []

            # prevent duplicated calls to callbacks
            # case (7)
            if scheduled_time in self.events:
                # test if callback in self.events[time]
                cbs = [c["id"] for c in self.events[scheduled_time]
                                                    if  c["action"] == action  and
                                                        c["args"] == task_args and
                                                        c["kwargs"] == task_kwargs]
                if len(cbs) > 0:
                    # return id of the first element. If there are more,
                    # something is very, very wrong...
                    if len(cbs) == 1:
                        return cbs[0]
                    raise IndexError(
                        "More than one entry in the scheduled events list match the time AND action")
            if rid is None:
                rid = self.task_id.get_id()
            event = {"action": action,
                     "period": period,
                     "current_execution": scheduled_time,
                     "last_execution": last_execution,
                     "id": rid,
                     "running": False,
                     "comment": comment,
                     "args": task_args,
                     "kwargs": task_kwargs
                     }

            try:
                self.current_mutex.acquire()
                # case (2)
                if self.current_time is None:
                    self.current_time = scheduled_time
                    self.current_event_actions = [event]
                    # ping the timer event to notify about a new task ready for execution
                    self.timer_event.set()
                    return event["id"]

                # case (3)
                if scheduled_time < self.current_time:
                    # requested time is before currently scheduled event.
                    # Save current event to the queue and schedule new arrival.
                    self.events[self.current_time] = self.current_event_actions
                    self.current_time = scheduled_time
                    self.current_event_actions = [event]
                    # set the event to signal that timeout has not passed,
                    # but new event has been scheduled for execution
                    self.timer_event.set()
                    return event["id"]

                # if time is the same as the upcoming event time, just add to the current queue.
                # No need to modify the self.events queue
                # cases (5),(6)
                if scheduled_time == self.current_time:
                    duplicates = [x["id"] for x in self.current_event_actions if
                                                    x["action"] == event["action"] and
                                                    x["args"] == task_args and
                                                    x["kwargs"] == task_kwargs]
                    if len(duplicates) == 0:
                        # case (6)
                        # add only if not already scheduled to run
                        # Return new event ID
                        self.current_event_actions.append(event)
                        return event["id"]
                    # case (5)
                    # Action with identical arguments is already on the execution list.
                    # This is just fall-through. No need to do anything
                    # no need to release mutex here. Will be released in finally
                    # Return ID of the event on the list
                    return duplicates[0]

                # If we get here, it's been already checked at the beginning if this is
                # new callback for the time
                # case (8)
                if scheduled_time in self.events:
                    callbacks = self.events[scheduled_time]
                    callbacks.append(event)
                    self.events.update({scheduled_time: callbacks})
                # case (4)
                else:
                    self.events[scheduled_time] = [event]
                return event["id"]
            finally:
                self.current_mutex.release()

            # "none of the above" - WTF? raise an exception.
            raise NotImplementedError(
                        "TimerThread.schedule_event() reached an unimplemented case for event %s"
                        % str(event))

        def status(self, timer_id):
            """
            Return information on status of a timer.

            Arguments:
                timer_id - id of the timer returned by schedule_event
            Returns:
                Record with information about the timer.
            Exceptions:
                KeyError - timer not found

            Structure of the returned record:
                id - id of the timer
                periodic - Boolean. True if timer is periodic.
                period - Period length for periodic tasks. None if not periodic
                scheduled_execution - time of the upcoming execution.
                last_execution - time of the previous execution for periodic
                                 tasks. None for non-periodic, or if first
                                 execution.
            """
            try:
                self.current_mutex.acquire()
                for e in self.current_event_actions:
                    if e['id'] == timer_id:
                        result = {
                            'id': timer_id,
                            'periodic': e['period'] is not None,
                            'period': e['period'],
                            'scheduled_execution': e['current_execution'],
                            'previous_execution': e['last_execution']
                        }
                        return result
                for t in self.events.keys():
                    for e in self.events[t]:
                        if e['id'] == timer_id:
                            result = {
                                'id': timer_id,
                                'periodic': e['period'] is not None,
                                'period': e['period'],
                                'scheduled_execution': e['current_execution'],
                                'previous_execution': e['last_execution']
                            }
                            return result
            finally:
                self.current_mutex.release()
            # If control got up to here, the id has not been found
            raise KeyError("timer not found", {"id": timer_id})

        def cancel_event(self, timer_id):
            """
            Method cancels a scheduled task. Returns True on successful cancelation,
            or False if task was not found.

            Arguments:
                timer_id - id of the task returned by TimerThread.schedule_event()

            Returns:
                True - cancelation was successful.
                False - task not found.
            """

            # TODO: remove from current_event_actions and events should be
            # independent
            try:
                self.current_mutex.acquire()
                events = [
                    e for e in self.current_event_actions if e["id"] == timer_id]
                if len(events) > 0:
                    # event is scheduled to be executed next.

                    # remove the event from the current list.
                    for e in events:
                        self.current_event_actions.remove(e)

                    # if the list is empty, take next one from the event queue.
                    if len(self.current_event_actions) == 0:
                        event_time = None
                        events = []
                        if len(self.events) > 0:
                            event_time, events = self.events.popitem(index=0)

                        self.current_time = event_time
                        self.current_event_actions = events
                        # ping the timer event
                        self.timer_event.set()
                    return True
                # event must be in the event queue, waiting for scheduling.
                matches = [(key, events) for (key, events) in self.events.items() if timer_id in
                           [x['id'] for x in events]]
                if len(matches) == 0:
                    # no matching events found in the scheduling queue
                    return False

                for ev_time, events in matches:
                    mm = [x for x in events if x['id'] == timer_id]
                    if len(mm) == 0:
                        return False
                    for m in mm:
                        events.remove(m)

                    # delete entry if no more events for the time
                    if len(events) == 0:
                        self.events.pop(ev_time)
                return True
            finally:
                self.current_mutex.release()

            return False

        def shutdown(self):
            """
            Shuts down the scheduler.

            If there is a pending event, its execution will be canceled.
            """
            # disable "running" state
            self.running = False
            # ping the timer to stop waiting
            self.timer_event.set()

        def run(self):
            """
            Thread worker.

            Somebody has to wo the heavy lifting.
            """
            while self.running:
                if self.current_time is not None:
                    wait_time = self.current_time - time.time()
                    # schedule wait only if scheduled wait is not
                    # close to current time.
                    if wait_time > self.dontwait_threshold:
                        self.timer_event.wait(wait_time)
                else:
                    # just wait for new request to start.
                    self.timer_event.wait()

                # if event is not set - timer expired.
                if not self.timer_event.is_set():
                    # save current execution time for rescheduling periodic
                    # timer. Used for reporting only.
                    current_execution_time = self.current_time
                    self.current_mutex.acquire()
                    # current_time = self.current_time
                    current_event_actions = self.current_event_actions

                    self.current_time = None
                    self.current_event_actions = []
                    if len(self.events) > 0:
                        event_time, events = self.events.popitem(index=0)
                        self.current_time = event_time
                        self.current_event_actions = events
                    self.current_mutex.release()

                    # start all callbacks
                    for event in current_event_actions:
                        if callable(event["action"]):
                            executor = TemporalScheduler.TimerThread.TimerExecutor(event["action"],
                                                                        self.executors,
                                                                        self.executors_mutex,
                                                                        task_args=event['args'],
                                                                        task_kwargs=event['kwargs'])

                            try:
                                self.executors_mutex.acquire()
                                self.executors.append(executor)
                            finally:
                                self.executors_mutex.release()
                            executor.start()
                        elif isinstance(event["action"], Event):
                            event["action"].set()

                        # if event is periodic - schedule next execution
                        if event["period"] is not None:
                            comment = event["comment"]
                            if comment is None:
                                comment = ""
                            self.schedule_event(event["action"],
                                                period=event["period"],
                                                comment=comment,
                                                rid=event["id"],
                                                task_args=event['args'],
                                                task_kwargs=event['kwargs'],
                                                last_execution=current_execution_time
                                                )


                self.timer_event.clear()

            # wait for all executors to finish running
            n = len(self.executors)
            for executor in self.executors:
                n -= 1
                executor.join()

    def __init__(self, time_epsilon = None):
        """
        Create and initialize TemporalScheduler object.

        The method creates and starts the timer thread.

        Arguments:
            time_epsilon - shortest distance between two events below which they
                            will be treated as executed at the same moment.
                            Default value: 0.01s
        """
        self.timer = TemporalScheduler.TimerThread()
        if time_epsilon is not None:
            self.timer.dontwait_threshold = time_epsilon
        self.timer.start()

    def status(self, timer_id):
        """
        Return status of the timer.

        Returns status from the internal timer object.
        """
        return self.timer.status(timer_id)

    def schedule_task(self,
                        callback,
                        absolute_time=None, delta_t=None, period=None,
                        comment=None,
                        task_args=None, task_kwargs=None):
        '''
        Schedule new task.
        Arguments:
            callback - function to call
            absolute_time - absolute time to execute the task
            delta_t - delay after which the task will be executed
                        (relative to current time)
            periodic - True if the task should be executed periodically.
                        delta_t contains period value.
            comment -  optional comment for the timer.
            task_args - positional arguments for the task
            task_kwargs - named arguments for the task
        Returns:
            id of the scheduled task
        Exceptions:
            ValueError if:
                - no execution time is provided (no absolute time nor delta_t)
                - absolute time and delta_t provided (what to use?)
        '''
        if absolute_time is None and delta_t is None and period is None:
            raise ValueError("%% No time information provided")
        if (absolute_time is not None) and (delta_t is not None):
            raise ValueError("%% Can't provide absolute time and delta_t")
        if absolute_time is not None:
            if absolute_time < time.time():
                raise ValueError("%% Need time machine. Send money")

        if task_args is None:
            task_args = ()
        if task_kwargs is None:
            task_kwargs = {}


        if period is not None:
            if absolute_time is None:
                absolute_time = time.time() + period
            return self.timer.schedule_event(callback,
                                             requested_time=absolute_time,
                                             period=period,
                                             comment=comment,
                                             task_args=task_args,
                                             task_kwargs=task_kwargs)

        if absolute_time is None:
            absolute_time = time.time() + delta_t

        return self.timer.schedule_event(callback,
                                         requested_time=absolute_time,
                                         comment=comment,
                                         task_args=task_args,
                                         task_kwargs=task_kwargs)

    def cancel_task(self, timer_id):
        """
        Cancel a scheduled task.

        Method cancels execution of a scheduled timer.
        Uses timer ID returned by schedule_task to identify the timer.
        """
        return self.timer.cancel_event(timer_id)

    def shutdown(self, wait_until_done=True):
        """
        Shut down the timer and wait for the thread to complete.

        Method shuts down the scheduler. All pending tasks are canceled,
        and the timer thread ordered to terminate. Method exits
        once the timer thread ends.
        """
        self.timer.shutdown()
        if wait_until_done:
            self.timer.join()
