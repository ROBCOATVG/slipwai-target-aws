#!/usr/bin/env python3
"""What this target needs on the machine, put there by the target: `./init` runs this first.

AWS is bootstrapped and deployed with OpenTofu and the AWS CLI. `./init` used to look for them and name what was
missing; now it runs this, which installs each one with whatever this machine installs things with —
`brew`, `apt`, `dnf`, `winget`, or the tool's own installer — or, with none of those, says where the tool's own page is, as before. A region is settled the same way: asked for at a terminal with `eu-west-2` on offer, taken as
that without one, and written to `infra/region`, which is where `scripts/bootstrap.py` looks. And the CLI's
sign-in is checked — `aws sts get-caller-identity` — with `aws configure` run at a terminal where it fails.

    python3 scripts/setup.py            # install what is missing, settle what is unset, sign in
    python3 scripts/setup.py --check    # say what would be done, and do nothing

Nothing here is the keel's: the keel runs this script and reads nothing from it, which is what keeps a
region, a package manager or a default a fact about AWS rather than a word the keel has to know.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Each tool, and the line that installs it per package manager, in the order they are tried. `sh` needs no
#: manager — it is the tool's own installer — so it comes last and always applies.
INSTALLS: dict[str, dict[str, str]] = {'aws': {'apt': 'sudo apt-get install -y awscli',
         'brew': 'brew install awscli',
         'dnf': 'sudo dnf install -y awscli',
         'winget': 'winget install --id Amazon.AWSCLI -e'},
 'tofu': {'brew': 'brew install opentofu',
          'sh': 'curl -fsSL https://get.opentofu.org/install-opentofu.sh -o '
                '/tmp/install-opentofu.sh && sh /tmp/install-opentofu.sh --install-method '
                'standalone && rm -f /tmp/install-opentofu.sh',
          'winget': 'winget install --id OpenTofu.Tofu -e'}}
#: Where each tool's own page is, for a machine with nothing that installs it.
WHERE = {'aws': 'https://aws.amazon.com/cli/', 'tofu': 'https://opentofu.org/docs/intro/install/'}
#: What each manager is looked for as on the PATH; `sh` is always there.
PROBES = {"brew": "brew", "apt": "apt-get", "dnf": "dnf", "winget": "winget", "sh": "sh"}
#: Where a project lives when nobody said. Offered at the prompt and taken without a terminal — a region has
#: to be settled for `make bootstrap`, and the one an account was opened in is as good a first answer as any;
#: `infra/region` is where it is remembered, which is the file `scripts/bootstrap.py` reads first.
DEFAULT_REGION = "eu-west-2"
REGION_FILE = ROOT / "infra/region"


def configured_region() -> str | None:
    if shutil.which("aws") is None:
        return None
    done = subprocess.run(["aws", "configure", "get", "region"], text=True, capture_output=True)
    return done.stdout.strip() or None


def settle_region(check: bool) -> None:
    """The region, if nothing says it yet: asked with the default on offer, or taken as the default, and
    written where `make bootstrap` reads it."""
    found = os.environ.get("AWS_REGION") or configured_region()
    if not found and REGION_FILE.is_file():
        found = REGION_FILE.read_text(encoding="utf-8").strip() or None
    if found:
        say(f"Region: {found}.")
        return
    if check:
        say(f"would settle the region: ask, offering {DEFAULT_REGION}, and write infra/region")
        return
    chosen = ""
    if sys.stdin.isatty():
        chosen = input(f"AWS region for this project [{DEFAULT_REGION}]: ").strip()
    region = chosen or DEFAULT_REGION
    REGION_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGION_FILE.write_text(region + "\n", encoding="utf-8")
    say(f"Region: {region}{' (the default; edit infra/region to change it)' if not chosen else ''} — wrote "
        f"infra/region; commit it with the bootstrap state.")


def signed_in() -> str | None:
    """Who the `aws` CLI is signed in as — the account, from `sts get-caller-identity` — or None."""
    if shutil.which("aws") is None:
        return None
    done = subprocess.run(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
                          text=True, capture_output=True)
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


def settle_sign_in(check: bool) -> bool:
    """Whether the CLI can reach an account. Not signed in and at a terminal, `aws configure` is run — the
    plain way in; a profile or SSO is named for a person who has one — and asked again."""
    if shutil.which("aws") is None:
        return False
    account = signed_in()
    if account:
        say(f"Signed in to AWS account {account}.")
        return True
    if check:
        say("would sign in: `aws configure`, or `aws sso login` / `AWS_PROFILE=<profile>` for an account that uses them")
        return False
    if not sys.stdin.isatty():
        say("Not signed in to AWS: run `aws configure`, `aws sso login --profile <name>`, or set AWS_PROFILE, then "
            "`make bootstrap`.")
        return False
    say("Not signed in to AWS. `aws configure` takes an access key; for SSO or a profile, Ctrl-C and run "
        "`aws sso login --profile <name>` or set AWS_PROFILE instead.")
    subprocess.run(["aws", "configure"])
    account = signed_in()
    say(f"Signed in to AWS account {account}." if account else
        "Still not signed in; `make bootstrap` will say so again when it is run.")
    return bool(account)


def say(line: str) -> None:
    print(line, flush=True)


def install(tool: str, check: bool) -> bool:
    """Put one tool here with the first manager this machine has, or say where it comes from. Whether it is
    there afterwards."""
    for manager, line in INSTALLS[tool].items():
        if shutil.which(PROBES[manager]) is None:
            continue
        say(f"{'would install' if check else 'Installing'} {tool}: {line}")
        if check:
            return False
        done = subprocess.run(line, shell=True)
        if done.returncode != 0:
            say(f"{tool}: that did not finish (exit {done.returncode}); see {WHERE[tool]}")
        return shutil.which(tool) is not None
    say(f"{tool}: nothing on this machine installs it (tried {', '.join(INSTALLS[tool])}); see {WHERE[tool]}")
    return False


def main(argv: list[str]) -> int:
    check = "--check" in argv
    short = [tool for tool in INSTALLS if shutil.which(tool) is None]
    if not short:
        say("OpenTofu and the AWS CLI: all here.")
    left = [tool for tool in short if not install(tool, check)]
    settle_region(check)
    settle_sign_in(check)
    if left and not check:
        say(f"Still missing: {', '.join(left)}. `./init` carries on without the push and bootstrap.")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
