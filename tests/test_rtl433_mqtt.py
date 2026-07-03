import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "rtl433-mqtt"


def run_dry(env=None):
    merged = os.environ.copy()
    merged.update(
        {
            "RTL433_MQTT_PRINT_COMMAND": "1",
            "HOSTNAME": "test-host",
            "PATH": os.environ.get("PATH", ""),
        }
    )
    if env:
        merged.update(env)
    return subprocess.run(
        [str(SCRIPT)],
        cwd=ROOT,
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class Rtl433MqttWrapperTests(unittest.TestCase):
    def test_default_command_uses_native_mqtt_and_jsonl_logging(self):
        result = run_dry()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("rtl_433", output)
        self.assertIn("-f", output)
        self.assertIn("433.92M", output)
        self.assertIn("-F", output)
        self.assertIn(
            "mqtt://localhost:1883,retain=0,base=rtl433/test-host,availability,events,states,devices",
            output,
        )
        self.assertIn("-F", output)
        self.assertIn("json:/var/log/rtl433-mqtt/rtl433-events.jsonl", output)
        self.assertIn("-M", output)
        self.assertIn("time:utc:iso:usec", output)
        self.assertNotIn("mosquitto_pub", output)

    def test_legacy_credentials_are_exported_but_redacted(self):
        result = run_dry(
            {
                "MQTT_USER": "old-user",
                "MQTT_PASS": "secret-pass",
                "MQTT_HOST": "mqtt.example.test",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MQTT_USERNAME=<redacted>", result.stdout)
        self.assertIn("MQTT_PASSWORD=<redacted>", result.stdout)
        self.assertNotIn("old-user", result.stdout)
        self.assertNotIn("secret-pass", result.stdout)

    def test_tls_command_adds_mqtts_and_certificate_options(self):
        result = run_dry(
            {
                "MQTT_TLS": "1",
                "MQTT_HOST": "broker.example.test",
                "MQTT_TLS_CA_CERT": "/etc/ssl/certs/ca.pem",
                "MQTT_TLS_CERT": "/etc/rtl433-mqtt/client.pem",
                "MQTT_TLS_KEY": "/etc/rtl433-mqtt/client.key",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout
        self.assertIn("mqtts://broker.example.test:8883", output)
        self.assertIn("tls_ca_cert=/etc/ssl/certs/ca.pem", output)
        self.assertIn("tls_cert=/etc/rtl433-mqtt/client.pem", output)
        self.assertIn("tls_key=/etc/rtl433-mqtt/client.key", output)

    def test_jsonl_logging_can_be_disabled(self):
        result = run_dry({"RTL433_LOG_JSONL": "0"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("json:/var/log/rtl433-mqtt/rtl433-events.jsonl", result.stdout)

    def test_fails_when_all_mqtt_categories_are_disabled(self):
        result = run_dry(
            {
                "MQTT_ENABLE_AVAILABILITY": "0",
                "MQTT_ENABLE_EVENTS": "0",
                "MQTT_ENABLE_STATES": "0",
                "MQTT_ENABLE_DEVICES": "0",
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least one MQTT output category", result.stderr)

    def test_fails_when_tls_cert_pair_is_incomplete(self):
        result = run_dry({"MQTT_TLS": "1", "MQTT_TLS_CERT": "/tmp/client.pem"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MQTT_TLS_CERT and MQTT_TLS_KEY must be set together", result.stderr)


class Rtl433MqttDeployTests(unittest.TestCase):
    def test_installer_uses_s500_shaped_paths_and_preserves_config(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn("INSTALL_DIR=/opt/rtl433-mqtt", installer)
        self.assertIn("CONFIG_DST=/etc/rtl433-mqtt/rtl433-mqtt.env", installer)
        self.assertIn("FORCE_CONFIG=0", installer)
        self.assertIn("--force-config", installer)
        self.assertIn("Keeping existing $CONFIG_DST", installer)
        self.assertIn("systemctl enable --now rtl433-mqtt.service", installer)

    def test_systemd_unit_matches_deployed_layout(self):
        unit = (ROOT / "deploy" / "rtl433-mqtt.service").read_text(encoding="utf-8")

        self.assertIn("After=local-fs.target", unit)
        self.assertIn("RequiresMountsFor=/var/log/rtl433-mqtt", unit)
        self.assertIn("EnvironmentFile=/etc/rtl433-mqtt/rtl433-mqtt.env", unit)
        self.assertIn("WorkingDirectory=/opt/rtl433-mqtt", unit)
        self.assertIn("ExecStart=/opt/rtl433-mqtt/rtl433-mqtt", unit)
        self.assertIn("Restart=always", unit)

    def test_logrotate_matches_s500_policy_without_copytruncate(self):
        config = (ROOT / "deploy" / "rtl433-mqtt-logrotate").read_text(
            encoding="utf-8"
        )

        self.assertIn("/var/log/rtl433-mqtt/*.jsonl", config)
        self.assertIn("daily", config)
        self.assertIn("rotate 30", config)
        self.assertIn("dateext", config)
        self.assertIn("dateformat _%Y-%m-%d", config)
        self.assertIn("compress", config)
        self.assertIn("create 0640 root root", config)
        self.assertIn("systemctl restart rtl433-mqtt.service", config)
        self.assertNotIn("copytruncate", config)

    def test_default_config_documents_runtime_controls(self):
        config = (ROOT / "config" / "rtl433-mqtt.env").read_text(encoding="utf-8")

        self.assertIn("MQTT_HOST=localhost", config)
        self.assertIn("MQTT_PORT=1883", config)
        self.assertIn("MQTT_TOPIC_PREFIX=rtl433", config)
        self.assertIn("RTL433_EVENT_LOG=/var/log/rtl433-mqtt/rtl433-events.jsonl", config)
        self.assertIn("RTL433_LOG_JSONL=1", config)
        self.assertIn("MQTT_ENABLE_AVAILABILITY=1", config)


class Rtl433MqttDocsTests(unittest.TestCase):
    def test_readme_covers_quick_install_and_update_docs(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("sudo ./install.sh", readme)
        self.assertIn("config/rtl433-mqtt.env", readme)
        self.assertIn("/etc/rtl433-mqtt/rtl433-mqtt.env", readme)
        self.assertIn("docs/rtl433-mqtt-service-deployment.md", readme)
        self.assertIn("rtl_433 -F help", readme)

    def test_deployment_doc_covers_operations_and_logs(self):
        doc = (ROOT / "docs" / "rtl433-mqtt-service-deployment.md").read_text(
            encoding="utf-8"
        )

        required = [
            "git pull --ff-only",
            "sudo ./install.sh --force-config",
            "sudo systemctl status rtl433-mqtt.service",
            "sudo journalctl -u rtl433-mqtt.service -f",
            "sudo systemctl restart rtl433-mqtt.service",
            "/var/log/rtl433-mqtt/rtl433-events.jsonl",
            "/etc/logrotate.d/rtl433-mqtt",
            "${base}/availability",
            "${base}/events",
            "${base}/states",
            "${base}/devices/",
            "rtl_433 -V",
            "rtl_433 -F help",
        ]
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, doc)

    def test_docs_include_topic_construction_examples(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        deployment = (ROOT / "docs" / "rtl433-mqtt-service-deployment.md").read_text(
            encoding="utf-8"
        )
        combined = readme + "\n" + deployment

        examples = [
            "MQTT_TOPIC_PREFIX=rtl433",
            "RECEIVER_ID=greenhouse",
            "rtl433/greenhouse/events",
            "MQTT_BASE_TOPIC=valpo/geomet/rtl433/stippler",
            "valpo/geomet/rtl433/stippler/devices/",
            "RECEIVER_ID defaults to the host name",
        ]
        for text in examples:
            with self.subTest(text=text):
                self.assertIn(text, combined)
