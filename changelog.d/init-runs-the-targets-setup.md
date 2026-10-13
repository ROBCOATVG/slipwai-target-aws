MINOR

**`./init` installs what bootstrapping AWS needs, through this package's own setup script.** The
package ships `scripts/setup.py` and names it as its `setup` hook, so `./init` runs it first: each tool —
OpenTofu and the AWS CLI — is installed with whatever the machine installs things with (`brew`, `apt`, `dnf`, `winget`, or the tool's own installer),
and a machine with none of those is told the tool's own page, as before. A region is settled the same way: asked for at a terminal with `eu-west-2` on offer, taken as that without one, and written to `infra/region`, which is where `scripts/bootstrap.py` looks.
The CLI's sign-in is checked too (`aws sts get-caller-identity`), with `aws configure` offered at a terminal where it fails.
`./init --no-install` only looks; `python3 scripts/setup.py --check` says what would be done.

**Catch-up:** `slipwai migrate` carries `scripts/setup.py` in and rewrites `./init`.
