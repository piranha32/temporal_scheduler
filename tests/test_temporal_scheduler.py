# pylint: disable=consider-using-f-string, invalid-name, consider-using-enumerate, attribute-defined-outside-init, wrong-import-position

"""
Performs unit tests on temporal scheduler
"""
import unittest
import time
import threading

from temporal_scheduler import TemporalScheduler


class TemporalSchedulerUnitTests(unittest.TestCase):
    """
    Class implements unit tests
    """
    def setUp(self) -> None:
        # error margin for comparing timestamps
        self.delta = 0.01

        self.ts = TemporalScheduler()
        return super().setUp()

    def doCleanups(self) -> None:
        self.ts.shutdown()
        return super().doCleanups()

    def testCreate(self):
        """
        Test creation of the object

        bla bla bla
        """
        self.assertIsNot(self.ts, None)


    def testCancelTaskSuccess(self):
        """
        Tests successfull cancellation of a scheduled task.
        """
        def function1():
            """
            does nothing    def testCancelTaskSuccessfull(self):

            """

        t_id = self.ts.schedule_task(function1, delta_t=1)
        self.assertIsNotNone(t_id)
        self.assertTrue(self.ts.cancel_task(t_id))


    def testCancelTaskFail(self):
        """
        Tests unsuccessfull cancellation of a scheduled task.
        """
        def function1():
            """
            does nothing
            """

        t_id = self.ts.schedule_task(function1, delta_t=1)
        self.assertIsNotNone(t_id)
        self.assertFalse(self.ts.cancel_task(t_id+1))


    def testCallbackArgs(self):
        """
        test passing args to the task
        """

        self.task_args = {}
        def task(x, y, z):
            self.task_args = {"time": time.time(), "x": x, "y": y, "z": z}

        task_id = self.ts.schedule_task(task, absolute_time = time.time() + 1,
                                    task_args = (1,), task_kwargs={'y': 20, 'z': 300})

        self.assertIsNot(task_id, None)
        time.sleep(2)

        self.assertEqual(len(self.ts.timer.current_event_actions), 0)
        self.assertEqual(len(self.ts.timer.events), 0)
        self.assertEqual(self.task_args['x'], 1)
        self.assertEqual(self.task_args['y'], 20)
        self.assertEqual(self.task_args['z'], 300)


    def testCallbackTemporalAccuracy(self):
        """
        test temporal accuracy of callback executions
        """

        self.task_traces = [[] for i in range(4)]

        def task(task_nb):
            """
            Performs action of the tests task.

            Function records execution time on each call.
            Takes one argument, indicating ID if the task.
            """

            self.task_traces[task_nb].append(time.time())

        base_time = time.time()
        self.ts.schedule_task(task,
                            delta_t = 5,
                            task_args = (0,),
                            comment="task1, rel time 5")
        t2id = self.ts.schedule_task(task,
                                period = 3,
                                task_args = (1,),
                                comment = "test2, periodic, period = 3")
        self.ts.schedule_task(task,
                        absolute_time = time.time() + 5,
                        task_args = (2,))
        self.ts.schedule_task(task,
                        absolute_time = time.time() + 1,
                        task_args = (3,))

        # Sleep for 20 seconds, giving time to execute tasks.
        time.sleep(20)

        # Cancel periodic task
        self.assertTrue(self.ts.cancel_task(t2id))

        # Verify execution times.
        # Max deviation from the expected execution time
        max_delta = 0.01

        # Expected execution times (delays)
        task_expected = [ [5],
                          [3, 6, 9, 12, 15, 18],
                          [5],
                          [1],
                        ]

        # Convert absolute execution times to relative
        for task_times in self.task_traces:
            for exec_nb in range(len(task_times)):
                task_times[exec_nb] -= base_time

        # Do the checks

        # Test 1: check length of the record list
        self.assertEqual(len(task_expected), len(self.task_traces))

        for i in range(len(task_expected)):
            # Test 2: check length of the record list for a task
            self.assertEqual(len(task_expected[i]), len(self.task_traces[i]),
                              msg = "Diff len for task %s" % i)

            for j in range(len(self.task_traces[i])):
                # Test 3: check times
                self.assertAlmostEqual(self.task_traces[i][j],
                                        task_expected[i][j],
                                        delta = max_delta,
                                        msg = "Diff in task %s, exec %s: e:%s -> a:%s" %
                                                  (i, j, task_expected[i][j],
                                                   self.task_traces[i][j]))

    def testSchedulingCase1(self):
        """
        case 1: time is in the past.

        This is a dup of a test from another test
        For details see TimerThread.schedule_event
        """
        def task():
            """
            dummy task
            """

        # case 1: time is in the past. Reject
        # This is a dup of a test from another test
        with self.assertRaises(ValueError,
                                msg = "Past task can be scheduled"):
            self.ts.schedule_task(task, absolute_time = time.time()-1)

    def testSchedulingCase2(self):
        """
        case 2: scheduling to an empty scheduler.

        For details see TimerThread.schedule_event
        """
        def task(status):
            """
            Task increments "counter" field in status dict
            """
            status["counter"] += 1

        # case 2: scheduling to an empty scheduler.
        status = {"counter": 0}

        # Task is scheduled to execute after 1 second
        self.ts.schedule_task(task,
                          absolute_time = time.time() + 1,
                          task_args = (status,))

        # Wait for 2 seconds for the task to execute
        time.sleep(2)

        self.assertEqual(status["counter"], 1, msg="Case 2 task did not execute")

    def testSchedulingCase3(self):
        """
        case 3: Scheduled task is earlier than current head

        For details see TimerThread.schedule_event
        """
        def task(task_id, status):
            """
            Task saves execution time to status list
            """
            status[task_id - 1] = time.time()

        # case 3: Scheduled task is earlier than current head
        status = [0, 0]
        current_time = time.time()

        # Task 1 is scheduled to execute after 2 seconds
        self.ts.schedule_task(task,
                          absolute_time = current_time + 2,
                          task_args = (1, status,))

        # Task 2is scheduled to execute prior to task 1
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1,
                          task_args = (2, status,))

        # Give both task time to complete
        time.sleep(3)

        self.assertAlmostEqual(status[0] - current_time, 2, delta = self.delta)
        self.assertAlmostEqual(status[1] - current_time, 1, delta = self.delta)



    def testSchedulingCase4(self):
        """
        case 4: New task, later than head, goes into the queue

        For details see TimerThread.schedule_event
        """
        def task():
            """
            dummy task
            """

        # case 4: New task, later than head, goes into the queue
        current_time = time.time()
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1)

        # Task 2is scheduled to execute prior to task 1
        self.ts.schedule_task(task,
                          absolute_time = current_time + 2)

        # Reach into the bowels of the scheduler and check:
        # 1. length of the execution list
        self.assertEqual(len(self.ts.timer.current_event_actions), 1)

        # 2. length of the scheduler queue
        self.assertEqual(len(self.ts.timer.events), 1)


    def testSchedulingCase5(self):
        """
        case 5: New task at the same time as head, duplicate of a task on the list
        For details see TimerThread.schedule_event
        """
        def task():
            """
            dummy task
            """

        # case 5: New task at the same time as head,
        #           duplicate of a task on the list
        current_time = time.time()
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1,
                          task_args=(1,))
        # check lengths of the execution list and the queue
        self.assertEqual(len(self.ts.timer.events), 0)
        self.assertEqual(len(self.ts.timer.current_event_actions), 1)

        #duplicate
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1,
                          task_args=(1,))
        # check lengths of the execution list and the queue
        self.assertEqual(len(self.ts.timer.events), 0)
        self.assertEqual(len(self.ts.timer.current_event_actions), 1)




    def testSchedulingCase6(self):
        """
        case 6: New task at the same time as head, new task added to the list

        For details see TimerThread.schedule_event
        """
        def task():
            """
            dummy task
            """

        # case 6: New task at the same time as head,
        #            new task added to the list
        current_time = time.time()
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1,
                          task_args=(1,))
        # check lengths of the execution list and the queue
        self.assertEqual(len(self.ts.timer.events), 0, msg = "Task added to events")
        self.assertEqual(len(self.ts.timer.current_event_actions), 1,
                                        msg = "task not added to current_event_actions")

        #duplicate
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1,
                          task_args=(2,))
        # check lengths of the execution list and the queue
        self.assertEqual(len(self.ts.timer.events), 0,
                                        msg = "Task added to events")
        self.assertEqual(len(self.ts.timer.current_event_actions), 2,
                                        msg = "task not added to current-event_actions")


    def testSchedulingCase7(self):
        """
        case 7: New task for the event queue (not head), duplicate of a task in the queue

        For details see TimerThread.schedule_event
        """
        def task():
            """
            dummy task
            """

        # case 7: New task for the event queue (not head),
        #           duplicate of a task in the queue
        current_time = time.time()
        # fill current_event_actions first
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1,
                          task_args=(1,))
        # sanity checks
        self.assertEqual(len(self.ts.timer.events), 0,
                                        msg = "Task added to events")
        self.assertEqual(len(self.ts.timer.current_event_actions), 1,
                                        msg = "task not added to current-event_actions")

        # task goes to events
        self.ts.schedule_task(task,
                          absolute_time = current_time + 2,
                          task_args=(1,))
        self.assertEqual(len(self.ts.timer.events), 1,
                                        msg = "Task added to events")
        self.assertEqual(len(self.ts.timer.current_event_actions), 1,
                                        msg = "task not added to current-event_actions")

        # dup!
        self.ts.schedule_task(task,
                          absolute_time = current_time + 2,
                          task_args=(1,))
        self.assertEqual(len(self.ts.timer.events), 1,
                                        msg = "Task added to events")
        self.assertEqual(len(self.ts.timer.current_event_actions), 1,
                                        msg = "task not added to current-event_actions")



    def testSchedulingCase8(self):
        """
         case 8: New task for the event queue (not head), new task added to the queue

        For details see TimerThread.schedule_event
        """
        def task():
            """
            dummy task
            """
        def task2():
            """
            dummy task
            """

        # case 8: New task for the event queue (not head),
        #           new task added to the queue
        current_time = time.time()
        # fill current_event_actions first
        self.ts.schedule_task(task,
                          absolute_time = current_time + 1,
                          task_args=(1,))
        # sanity checks
        self.assertEqual(len(self.ts.timer.events), 0,
                                        msg = "Task added to events")
        self.assertEqual(len(self.ts.timer.current_event_actions), 1,
                                        msg = "task not added to current-event_actions")

        # task goes to events
        self.ts.schedule_task(task,
                          absolute_time = current_time + 2,
                          task_args=(1,))
        self.assertEqual(len(self.ts.timer.events), 1,
                                        msg = "Task added to events")
        self.assertEqual(len(self.ts.timer.current_event_actions), 1,
                                        msg = "task not added to current-event_actions")

        # Other tasks
        # add kwargs
        self.ts.schedule_task(task,
                          absolute_time = current_time + 2,
                          task_args=(1,),
                          task_kwargs=(1,))
        # change task
        self.ts.schedule_task(task2,
                          absolute_time = current_time + 2,
                          task_args=(1,))
        #change args
        self.ts.schedule_task(task,
                          absolute_time = current_time + 2,
                          task_args=(2,))
        # Change time
        self.ts.schedule_task(task,
                          absolute_time = current_time + 3,
                          task_args=(1,))


        # There are 4 different tasks for t+2
        self.assertEqual(len(self.ts.timer.events[current_time + 2]), 4,
                                        msg = "Tasks not added to events tor t+2")
        # There is one task for t+3
        self.assertEqual(len(self.ts.timer.events[current_time + 3]), 1,
                                        msg = "Task not added to events for t+3")
        # There is one task waiting for execution
        self.assertEqual(len(self.ts.timer.current_event_actions), 1,
                                        msg = "task not added to current-event_actions")



    def testStatus(self):
        """
        Test retrieval of task status
        """

        self.task_traces = [[] for i in range(4)]

        def task(task_nb):
            """
            Performs action of the tests task.

            Function records execution time on each call.
            Takes one argument, indicating ID if the task.
            """

            self.task_traces[task_nb].append(time.time())

        scheduled_time = time.time() + 1
        t1_id = self.ts.schedule_task(task,
                          absolute_time = scheduled_time,
                          task_args = (1,))

        status = self.ts.status(t1_id)
        expected_status = {'id': 0,
                            'periodic': False,
                            'period': None,
                            'scheduled_execution': scheduled_time,
                            'previous_execution': None}
        self.assertEqual(status, expected_status)


    def testScheduleTaskFail(self):
        """
        Test situations when task scheduling is expected to fail
        """

        def task():
            """
            dummy task
            """

        with self.assertRaises(ValueError,
                                msg = "Task with no exec time can be scheduled"):
            self.ts.schedule_task(task)

        with self.assertRaises(ValueError,
                                msg = "Past task can be scheduled"):
            self.ts.schedule_task(task, absolute_time = time.time()-1)

        with self.assertRaises(ValueError,
                                msg = "Task with delta and absolute time can be scheduled"):
            self.ts.schedule_task(task, absolute_time = time.time()+1, delta_t=1)


    def testSchedulingEvents(self):
        """
        Test handling of thread synchronization using threading.Event
        """
        class eventAction(threading.Thread):
            """
            Implements a test thread waiting for an event.

            Class records time of each activation for further analysis
            """
            def __init__(self, sync):
                threading.Thread.__init__(self)
                self.sync = sync
                self.counter = 0

                # helper function to execute the threads
            def run(self):
                # wait for the event for max 5 seconds.
                self.sync.wait(5)
                if self.sync.is_set():
                    self.counter += 1
                self.sync.clear()


        sync = threading.Event()
        thread1 = eventAction(sync)
        thread1.start()

        self.ts.schedule_task(sync, delta_t = 1)

        self.assertEqual(thread1.counter, 0)
        # Start the threads and wait until they complete
        thread1.join()
        self.assertEqual(thread1.counter, 1)


    def testEventsTemporalAccuracy(self):
        """
        Test temporal accuracy of thread synchronization using threading.Event
        """

        class eventAction(threading.Thread):
            """
            Implements a test thread waiting for an event.

            Class records time of each activation for further analysis
            """
            def __init__(self, thread_id, sync, time_track, max_runs = 5):
                threading.Thread.__init__(self)
                self.thread_id = thread_id
                self.sync = sync
                self.track = time_track
                self.counter = 0
                self.max_runs = max_runs

            def run(self):
                while self.counter < self.max_runs:
                    # wait for the event for max 5 seconds.
                    # Record the time of the event, or -1 if timeout occurred
                    trigger_time = -1
                    if self.sync.wait(5):
                        trigger_time = time.time()
                    self.sync.clear()

                    self.track.append(trigger_time)
                    self.counter += 1

        sync = threading.Event()
        traces = [[], []]
        thread1_repeats = 50
        thread2_repeats = 10
        thread1 = eventAction(1, sync, traces[0], thread1_repeats)
        thread2 = eventAction(2, sync, traces[1], thread2_repeats)

        event_period = 0.03
        base_time = time.time()
        t_id = self.ts.schedule_task(sync, period = event_period)

        # Start the threads and wait until they complete
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # shut down synchronization task
        self.ts.cancel_task(t_id)


        # check for timeouts
        for task in range(2):
            for events in traces[task]:
                self.assertGreaterEqual(events, 0, msg = "Timeout in thread %s" % task)

        # Convert absolute execution times to relative
        for task_trace in traces:
            for i in range(len(task_trace)):
                task_trace[i] -= base_time

        # check for trigger time accuracy
        expected_times = [
                            [event_period * (i+1) for i in range(thread1_repeats)],
                            [event_period * (i+1) for i in range(thread2_repeats)]
                          ]
        for task in range(2):
            self.assertEqual(len(traces[task]), len(expected_times[task]),
                              msg = "Diff len for task %s" % task)
            for i in range(len(traces[task])):
                self.assertAlmostEqual(expected_times[task][i],
                                        traces[task][i],
                                        delta = 0.01,
                                        msg= "Diff exec ime in task %i: e: %s -> a:%s" %
                                                  ( task,
                                                    expected_times[task][i],
                                                    traces[task][i]))
