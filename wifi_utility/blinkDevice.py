from dataclasses import dataclass

from gpiozero import DigitalOutputDevice


@dataclass
class BlinkDeviceConfig:
    gpio_number: int
    active_high: bool
    initial_value: bool


class BlinkDevice:

    def open(self) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        raise NotImplementedError()

    def on(self) -> None:
        raise NotImplementedError()

    def off(self) -> None:
        raise NotImplementedError()


class GpioBlinkDevice(BlinkDevice):

    def __init__(self, gpio_number: int, active_high: bool, initial_value: bool) -> None:
        self._gpio_number = gpio_number
        self._active_high = active_high
        self._initial_value = initial_value
        self._device = None

    def open(self) -> None:
        if not self._device:
            self._device = DigitalOutputDevice(
                self._gpio_number, active_high=self._active_high, initial_value=self._initial_value
            )

    def close(self) -> None:
        if self._device:
            self._device.close()
            self._device = None

    def on(self) -> None:
        if self._device:
            self._device.on()

    def off(self) -> None:
        if self._device:
            self._device.off()
