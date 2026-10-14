"""Where the passphrase that decrypts the committed bootstrap state lives after the first run: in the account.

The apply that writes it ends in somebody's account and is unprovable here. What is proved is the script's
side of it — a set passphrase wins, a first run makes one, a later run reads the account's copy back with the
`aws` CLI, and an account that has none says what to set rather than failing on an unreadable state — and that
the stack declares the parameter the script reads.
"""
from __future__ import annotations

import importlib.util
import io
import contextlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]


def module(root: Path):
    spec = importlib.util.spec_from_file_location("bootstrap_passphrase_test", PACKAGE / "scripts/bootstrap.py")
    assert spec and spec.loader
    found = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(found)
    found.ROOT = root
    found.STACK = root / "infra/bootstrap"
    found.STATE = found.STACK / "terraform.tfstate"
    found.STACK.mkdir(parents=True)
    (found.STACK / "project.auto.tfvars.json").write_text('{"project": "demo", "services": {}}\n', encoding="utf-8")
    return found


class PassphraseTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.script = module(Path(directory.name))

    def test_the_stack_keeps_it_in_the_account_as_a_secure_string(self) -> None:
        stack = (PACKAGE / "bootstrap/main.tf").read_text(encoding="utf-8")
        self.assertIn('resource "aws_ssm_parameter" "state_passphrase"', stack)
        self.assertIn('name  = "/${var.project}/bootstrap/state-passphrase"', stack)
        self.assertIn('type  = "SecureString"', stack)
        self.assertEqual(self.script.parameter_name(), "/demo/bootstrap/state-passphrase")
        self.assertIn("ssm:PutParameter", self.script.NEEDED_ACTIONS, "the pre-apply check asks for what the apply does")

    def test_a_set_passphrase_wins_and_nothing_is_asked_of_the_account(self) -> None:
        with mock.patch.dict("os.environ", {"TF_VAR_state_passphrase": "the-one-they-set"}), \
                mock.patch.object(self.script.subprocess, "run") as run:
            self.assertEqual(self.script.passphrase({}), ("the-one-they-set", False))
        run.assert_not_called()

    def test_a_first_run_makes_one_long_enough_for_the_key_provider(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            phrase, fresh = self.script.passphrase({})
        self.assertTrue(fresh)
        self.assertGreaterEqual(len(phrase), 16)

    def test_a_later_run_reads_the_account_s_copy_back(self) -> None:
        self.script.STATE.write_text("{}", encoding="utf-8")
        asked = []

        def aws(command, **options):
            asked.append(command)
            return subprocess.CompletedProcess(command, 0, stdout="kept-by-the-account\n", stderr="")

        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(self.script.subprocess, "run", aws), \
                contextlib.redirect_stderr(io.StringIO()) as said:
            self.assertEqual(self.script.passphrase({"AWS_REGION": "eu-west-2"}), ("kept-by-the-account", False))
        self.assertEqual(asked[0][:4], ["aws", "ssm", "get-parameter", "--name"])
        self.assertEqual(asked[0][4], "/demo/bootstrap/state-passphrase")
        self.assertIn("--with-decryption", asked[0])
        self.assertIn("read back from the account", said.getvalue())

    def test_an_account_with_no_copy_says_what_to_set_instead_of_failing_on_the_state(self) -> None:
        """A project bootstrapped before the stack kept one, or a sign-in that may not read it."""
        self.script.STATE.write_text("{}", encoding="utf-8")
        refused = subprocess.CompletedProcess([], 254, stdout="", stderr="ParameterNotFound")
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch.object(self.script.subprocess, "run", lambda *a, **k: refused), \
                self.assertRaises(self.script.Failure) as caught:
            self.script.passphrase({})
        self.assertIn("TF_VAR_state_passphrase", str(caught.exception))
        self.assertIn("/demo/bootstrap/state-passphrase", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
