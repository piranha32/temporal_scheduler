import threading
import time
from temporal_scheduler import TemporalScheduler

class eventAction(threading.Thread):
    """
    Implements a test thread waiting for an event.

    Class records time of each activation for further analysis
    """
    def __init__(self, thread_id, sync):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.sync = sync

    def run(self):
        # wait for the event for max 5 seconds.
        if self.sync.wait(5):
            print("Thread %s: event fired" % self.thread_id)
        else:
            print("*** Thread %s: event timed out" % self.thread_id)
        self.sync.clear()


ts = TemporalScheduler()
sync_event = threading.Event()

print("Starting worker thread")
thread1 = eventAction(1, sync_event)
thread1.start()


print("Scheduling the event to start in 4 seconds\n")
ev_id = ts.schedule_task(sync_event, delta_t = 4)

print("Waiting for 3 seconds\n")
time.sleep(3)

print("Cancelling event")
ts.cancel_task(ev_id)

print("Sleeping for another 3 seconds.")
print("In 2 seconds you should see a message from the thread about event timeout\n")
time.sleep(3)

# Start the threads and wait until they complete
thread1.join()

print("\nBy now the event should have timed out, and the thread completed. Time to shut down")
ts.shutdown()
