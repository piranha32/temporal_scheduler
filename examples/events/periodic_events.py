import threading
from temporal_scheduler import TemporalScheduler

class EventAction(threading.Thread):
    """
    Implements a test thread waiting for an event.

    Class records time of each activation for further analysis
    """
    def __init__(self, thread_id, sync):
        threading.Thread.__init__(self)
        self.counter = 0
        self.thread_id = thread_id
        self.sync = sync

    def run(self):
        while self.counter < 5:
            # wait for the event for max 5 seconds.
            if self.sync.wait(5):
                print("Thread %s: event fired" % self.thread_id)
            else:
                print("Thread %s: event timed out" % self.thread_id)
            self.sync.clear()
            self.counter += 1

ts = TemporalScheduler()
sync_event = threading.Event()
thread1 = EventAction(1, sync_event)
thread2 = EventAction(2, sync_event)
thread1.start()
thread2.start()


print("Scheduling the event to execute once a second")
t_id = ts.schedule_task(sync_event, period = 1)

# Start the threads and wait until they complete
thread1.join()
thread2.join()

print("All done")
ts.shutdown()
