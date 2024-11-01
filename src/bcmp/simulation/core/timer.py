from datetime import datetime, timedelta


DEFAULT_TIMER_PRECISION = 1e-3  # seconds

type Time = datetime
type TimeDiff = timedelta


class Timer:
    def __init__(self, precision: float = DEFAULT_TIMER_PRECISION) -> None:
        self._precision = precision

        self._time: Time = datetime.min
        self._resolution: TimeDiff = timedelta(seconds=precision)

    @property
    def time(self) -> Time:
        return self._time

    @property
    def ts(self) -> str:
        return self._time.strftime("%M:%S:%f")[:-3]

    @property
    def resolution(self) -> TimeDiff:
        return self._resolution

    def tick(self) -> None:
        self._time += self._resolution

    def round(self, seconds: float) -> TimeDiff:
        return timedelta(seconds=round(seconds / self._precision) * self._precision)
