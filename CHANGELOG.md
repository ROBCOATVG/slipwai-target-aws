# Changelog

No releases yet. Release notes are recorded here newest first, one entry per released version; the entry being
written is `changelog.d/`.

## 1.1.0 — MINOR

**`./init` installs what bootstrapping AWS needs, through this package's own setup script.** The
package ships `scripts/setup.py` and names it as its `setup` hook, so `./init` runs it first: each tool —
OpenTofu and the AWS CLI — is installed with whatever the machine installs things with (`brew`, `apt`, `dnf`, `winget`, or the tool's own installer),
and a machine with none of those is told the tool's own page, as before. A region is settled the same way: asked for at a terminal with `eu-west-2` on offer, taken as that without one, and written to `infra/region`, which is where `scripts/bootstrap.py` looks.
The CLI's sign-in is checked too (`aws sts get-caller-identity`), with `aws configure` offered at a terminal where it fails.
`./init --no-install` only looks; `python3 scripts/setup.py --check` says what would be done.

**Catch-up:** `slipwai migrate` carries `scripts/setup.py` in and rewrites `./init`.

## 1.0.0

**AWS ships as a target package: `slipwai target install aws`, and `--target aws` is offered.** Everything
a project going to AWS is given is here rather than in the keel — the account stack and the service stack, the
scripts that bootstrap and deploy, the deployment drawing and the production decision record, the tools `./init`
checks for, the parts of the pipeline that are AWS's, and the answers that exist only here.

The keel it is built against names no cloud. That is the whole point of the move: a second place to deploy to is a
package somebody publishes, not a branch somebody adds to `generate`.

**Catch-up:** a project already generated with `--target aws` is unchanged. A keel upgraded past the move needs
`slipwai target install aws` before it will generate another one.

