from dataclasses import dataclass
from datetime import datetime
from time import sleep

from gpiozero import DigitalOutputDevice


@dataclass
class BlinkConfig:
    frequency: float = 500
    interval: float = 0.5
    pause: float = 0.5
    count: int = 3


class IBlinkControl:

    def blink(self) -> None:
        raise NotImplementedError()


class BlinkControl(IBlinkControl):

    def __init__(self, config: BlinkConfig, device: DigitalOutputDevice) -> None:
        self._config = config
        self._device = device

    def blink(self) -> None:
        interval_micros = self._config.interval * 1_000_000
        period = 1 / self._config.frequency

        for count in range(self._config.count):
            self._blink(interval_micros, period)

            if count < self._config.count - 1:
                sleep(self._config.pause)

    def _blink(self, interval_micros: float, period: float) -> None:
        start_time = datetime.now()

        while True:
            elapsed = datetime.now() - start_time
            elapsed_micros = elapsed.total_seconds() * 1_000_000 + elapsed.microseconds
            if elapsed_micros < interval_micros:
                self._device.on()
                sleep(period / 2)
                self._device.off()
                sleep(period / 2)
            else:
                break
