from dataclasses import dataclass
from datetime import datetime
from time import sleep

from context_logger import get_logger

from wifi_utility.blinkDevice import BlinkDevice

log = get_logger('BlinkControl')


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

    def __init__(self, config: BlinkConfig, device: BlinkDevice) -> None:
        self._config = config
        self._device = device

    def blink(self) -> None:
        interval_micros = self._config.interval * 1_000_000
        half_period = (1 / self._config.frequency) / 2

        try:
            self._device.open()

            for count in range(self._config.count):
                self._blink(interval_micros, half_period)

                if count < self._config.count - 1:
                    sleep(self._config.pause)
        except Exception as error:
            log.error(f"Blink device error: {error}")
        finally:
            self._device.close()

    def _blink(self, interval_micros: float, half_period: float) -> None:
        start_time = datetime.now()

        while True:
            elapsed = datetime.now() - start_time
            elapsed_micros = elapsed.total_seconds() * 1_000_000 + elapsed.microseconds
            if elapsed_micros < interval_micros:
                self._device.on()
                sleep(half_period)
                self._device.off()
                sleep(half_period)
            else:
                break
