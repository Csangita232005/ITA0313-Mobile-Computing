import unittest
from src.task6_tracking import choose_policy
from src.task5_power import evaluate_power_state
from src.task4_security import audit, DEFAULT_CONFIG

class PolicyTests(unittest.TestCase):
    def test_low_battery_stationary_defers_upload(self):
        scenario = {"battery":20,"charging":False,"network":"lte","motion":"stationary",
                    "temperature_c":30,"low_power":False,"queued":10}
        interval, upload, _ = choose_policy(scenario)
        self.assertEqual(interval, 120)
        self.assertEqual(upload, "DEFER_TO_WIFI_OR_CHARGING")

    def test_no_network_queues_offline(self):
        scenario = {"battery":55,"charging":False,"network":"none","motion":"moving",
                    "temperature_c":28,"low_power":False,"queued":10}
        self.assertEqual(choose_policy(scenario)[1], "QUEUE_OFFLINE")

    def test_critical_battery_uses_saver(self):
        scenario = {"battery":10,"charging":False,"network":"lte","motion":"stationary",
                    "temperature_c":28,"low_power":True,"queued":10}
        self.assertEqual(choose_policy(scenario)[0], 180)

    def test_hot_device_reduces_work(self):
        scenario = {"battery":48,"charging":False,"network":"wifi","motion":"moving",
                    "temperature_c":44,"low_power":False,"queued":10}
        self.assertEqual(choose_policy(scenario)[1], "DEFER_UNTIL_COOLER")

    def test_power_state_low_battery(self):
        self.assertEqual(evaluate_power_state(False, False, 10, False), "LOW_POWER")

    def test_security_audit_detects_cleartext(self):
        config = dict(DEFAULT_CONFIG)
        config["network_endpoints"] = [{"url":"http://test.invalid","protocol":"HTTP","tls_validation":False}]
        rows = audit(config)
        self.assertTrue(any(row[3] == "EXPOSED" for row in rows))

if __name__ == "__main__":
    unittest.main()
