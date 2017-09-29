# stdlib
import time

class StsTimer(object):
    def __init__(self, timer_name, interval_seconds):
        self.timer_name = timer_name
        self.interval_seconds = interval_seconds
        self.reset()

    def reset(self):
        self.last_tick_time = self._current_time_seconds()

    def load(self, persistable_store):
        self.last_tick_time = persistable_store[self.timer_name]
        if not self.last_tick_time:
            self.last_tick_time = self._current_time_seconds() - self.interval_seconds

    def persist(self, persistable_store):
        persistable_store[self.timer_name] = self.last_tick_time

    def expired(self):
        return self._current_time_seconds() >= self.last_tick_time + self.interval_seconds

    def _current_time_seconds(self):
        return int(round(time.time()))

class Timer(object):
    """ Helper class """

    def __init__(self):
        self.start()

    def _now(self):
        return time.time()

    def start(self):
        self.started = self._now()
        self.last = self.started
        return self

    def step(self):
        now = self._now()
        step = now - self.last
        self.last = now
        return step

    def total(self, as_sec=True):
        return self._now() - self.started
