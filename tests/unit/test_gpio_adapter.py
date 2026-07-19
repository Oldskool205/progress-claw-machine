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

    def test_gpio_initialization_failure_is_not_reported_as_mock_success(self):
        def failing_factory(*args, **kwargs):
            raise RuntimeError("GPIO permission denied")

        adapter = GpioArduinoAdapter(output_device_factory=failing_factory)

        response = adapter.send_command("PLAY START 60")

        self.assertFalse(response.ok)
        self.assertFalse(response.mock)
        self.assertFalse(adapter.connected)
        self.assertIn("GPIO permission denied", response.message)

    def test_lost_gpio_outputs_are_reopened_before_the_next_command(self):
        class RecoverableOutput(FakeOutput):
            created = []

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.closed = False
                self.created.append(self)

            def close(self):
                self.closed = True

        adapter = GpioArduinoAdapter(output_device_factory=RecoverableOutput)
        self.assertTrue(adapter.send_command("CLAW POWER 70").ok)
        original_outputs = list(RecoverableOutput.created)
        original_outputs[0].closed = True

        response = adapter.send_command("PLAY START 60")

        self.assertTrue(response.ok)
        self.assertEqual(len(RecoverableOutput.created), 8)
        self.assertTrue(all(output.closed for output in original_outputs))
        self.assertTrue(adapter._start_output.value)


if __name__ == "__main__":
    unittest.main()
