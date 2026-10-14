"""The GitHub OIDC provider is the account's, not the project's: one per issuer URL, reused by every project
after the first and owned by none of them that did not create it.

The apply ends in somebody's account and is unprovable here. What is proved is the script's side — the lookup,
the three answers (create, reuse, keep what this state owns) and the permission it stops asking for — and that
the stack creates the provider only where it was handed none and names whichever one it has in the trust.
"""
from __future__ import annotations

import importlib.util
import io
import contextlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
ARN = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"


def module(root: Path):
    spec = importlib.util.spec_from_file_location("bootstrap_provider_test", PACKAGE / "scripts/bootstrap.py")
    assert spec and spec.loader
    found = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(found)
    found.ROOT = root
    found.STACK = root / "infra/bootstrap"
    found.STATE = found.STACK / "terraform.tfstate"
    found.STACK.mkdir(parents=True)
    return found


def answering(table: dict[str, tuple[int, str]]):
    """A `subprocess.run` that answers by the command's first words, recording what was asked."""
    asked = []

    def run(command, **options):
        asked.append(command)
        for head, (code, out) in table.items():
            if " ".join(command).startswith(head):
                return subprocess.CompletedProcess(command, code, stdout=out, stderr="")
        raise AssertionError(f"unexpected command {command}")
    return run, asked


class ProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.script = module(Path(directory.name))
        self.listing = json.dumps({"OpenIDConnectProviderList": [
            {"Arn": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.eu-west-2.amazonaws.com/id/ABC"},
            {"Arn": ARN},
        ]})

    def test_the_stack_creates_the_provider_only_where_it_was_handed_none(self) -> None:
        stack = (PACKAGE / "bootstrap/main.tf").read_text(encoding="utf-8")
        self.assertIn('count = local.oidc && var.github_oidc_provider_arn == "" ? 1 : 0', stack)
        self.assertIn("identifiers = [local.github_oidc_arn]", stack)
        self.assertNotIn("aws_iam_openid_connect_provider.github[0].arn", stack)
        self.assertIn('variable "github_oidc_provider_arn"', (PACKAGE / "bootstrap/variables.tf").read_text(encoding="utf-8"))

    def test_the_account_s_github_provider_is_found_among_the_others(self) -> None:
        run, asked = answering({"aws iam list-open-id-connect-providers": (0, self.listing)})
        with mock.patch.object(self.script.subprocess, "run", run):
            self.assertEqual(self.script.existing_github_provider({}), ARN)
        run, _ = answering({"aws iam list-open-id-connect-providers": (0, json.dumps({"OpenIDConnectProviderList": []}))})
        with mock.patch.object(self.script.subprocess, "run", run):
            self.assertIsNone(self.script.existing_github_provider({}))
        run, _ = answering({"aws iam list-open-id-connect-providers": (254, "")})
        with mock.patch.object(self.script.subprocess, "run", run):
            self.assertIsNone(self.script.existing_github_provider({}), "a CLI that cannot say is not an account with none")

    def test_a_first_project_creates_and_a_second_reuses(self) -> None:
        run, _ = answering({"aws iam list-open-id-connect-providers": (0, json.dumps({"OpenIDConnectProviderList": []}))})
        with mock.patch.object(self.script.subprocess, "run", run), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.script.reused_provider("oidc", {}), "")
        run, asked = answering({"aws iam list-open-id-connect-providers": (0, self.listing)})
        with mock.patch.object(self.script.subprocess, "run", run), contextlib.redirect_stderr(io.StringIO()) as said:
            self.assertEqual(self.script.reused_provider("oidc", {}), ARN)
        self.assertIn("reused, not created", said.getvalue())
        self.assertFalse(any(command[:1] == ["tofu"] for command in asked), "no state yet, so nothing to list")

    def test_a_project_whose_state_owns_the_provider_keeps_it(self) -> None:
        """Told to reuse the account's, it would destroy its own — and every trust in the account with it."""
        self.script.STATE.write_text("{}", encoding="utf-8")
        run, asked = answering({"aws iam list-open-id-connect-providers": (0, self.listing),
                                "tofu": (0, "aws_s3_bucket.state\naws_iam_openid_connect_provider.github[0]\n")})
        with mock.patch.object(self.script.subprocess, "run", run), contextlib.redirect_stderr(io.StringIO()) as said:
            self.assertEqual(self.script.reused_provider("oidc", {}), "")
        self.assertIn("kept, as before", said.getvalue())
        self.assertIn("state", asked[-1])

    def test_an_access_key_forge_asks_nothing(self) -> None:
        with mock.patch.object(self.script.subprocess, "run") as run:
            self.assertEqual(self.script.reused_provider("access-key", {}), "")
        run.assert_not_called()

    def test_reusing_does_not_ask_for_the_permission_to_create(self) -> None:
        seen = []

        def simulate(command, **options):
            seen.append(command)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"EvaluationResults": []}), stderr="")
        identity = {"Arn": "arn:aws:iam::123456789012:user/admin", "Account": "123456789012"}
        with mock.patch.object(self.script.subprocess, "run", simulate):
            self.script.check_permissions(identity, "oidc", creating_provider=False)
            self.assertNotIn("iam:CreateOpenIDConnectProvider", seen[-1])
            self.script.check_permissions(identity, "oidc", creating_provider=True)
            self.assertIn("iam:CreateOpenIDConnectProvider", seen[-1])


if __name__ == "__main__":
    unittest.main()
