import unittest

from controller.adapters.arduino_adapter import ArduinoAdapter


class ArduinoAdapterTest(unittest.TestCase):
    def test_force_mock_records_commands_without_serial_connection(self):
        adapter = ArduinoAdapter(force_mock=True)

        response = adapter.send_command("PLAY START 10")

        self.assertTrue(response.ok)
        self.assertTrue(response.mock)
        self.assertEqual(response.message, "OK MOCK PLAY START 10")
        self.assertEqual(adapter.mock_commands, ("PLAY START 10",))
        self.assertFalse(adapter.connected)

    def test_empty_command_is_rejected(self):
        adapter = ArduinoAdapter(force_mock=True)

        response = adapter.send_command("   ")

        self.assertFalse(response.ok)
        self.assertEqual(response.message, "ERR EMPTY_COMMAND")


if __name__ == "__main__":
    unittest.main()
