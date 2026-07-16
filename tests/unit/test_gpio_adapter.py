import unittest

from controller.adapters.gpio_adapter import GpioArduinoAdapter


class FakeOutput:
    def __init__(self, pin, active_high=True, initial_value=False):
        self.pin = pin
        self.active_high = active_high
        self.value = initial_value

    def on(self):
        self.value = True

    def off(self):
        self.value = False

    def close(self):
        pass


class GpioArduinoAdapterTest(unittest.TestCase):
    def make_adapter(self):
        return GpioArduinoAdapter(output_device_factory=FakeOutput)

    def test_start_pulls_active_low_gate_on(self):
        adapter = self.make_adapter()

        response = adapter.send_command("PLAY START 60")

        self.assertTrue(response.ok)
        self.assertFalse(response.mock)
        self.assertTrue(adapter._start_output.value)
        self.assertFalse(adapter._start_output.active_high)

    def test_power_command_drives_three_bit_level(self):
        adapter = self.make_adapter()

        adapter.send_command("CLAW POWER 70")

        self.assertEqual([pin.value for pin in adapter._power_outputs], [True, True, False])

    def test_normal_stop_releases_gate_with_end_pulse_code(self):
        adapter = self.make_adapter()
        adapter.send_command("PLAY START 60")

        adapter.send_command("PLAY STOP")

        self.assertFalse(adapter._start_output.value)
        self.assertEqual([pin.value for pin in adapter._power_outputs], [True, True, True])

    def test_emergency_stop_releases_gate_without_pulse(self):
        adapter = self.make_adapter()
        adapter.send_command("PLAY START 60")

        adapter.send_command("EMERGENCY STOP")

        self.assertFalse(adapter._start_output.value)
        self.assertEqual([pin.value for pin in adapter._power_outputs], [False, False, False])


if __name__ == "__main__":
    unittest.main()
