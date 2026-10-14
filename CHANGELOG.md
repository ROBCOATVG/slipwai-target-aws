# Changelog

No releases yet. Release notes are recorded here newest first, one entry per released version; the entry being
written is `changelog.d/`.

## 1.2.1 — PATCH

**A second project in the same account reuses the account's GitHub OIDC provider instead of failing to
create it.** An account holds one provider per issuer URL, and GitHub's is the same URL for every project, so
the second `make bootstrap` into an account ended in `EntityAlreadyExists` on
`aws_iam_openid_connect_provider.github`. The script now looks the provider up and hands the stack its ARN;
the stack creates one only where the account has none. A reused provider is never in the project's state,
so tearing one project down leaves every other project's trust standing — and a project whose state already
owns the provider keeps owning it rather than being told to reuse, and destroy, itself. The pre-apply
permission check no longer asks for `iam:CreateOpenIDConnectProvider` when nothing will be created.

**Catch-up:** `slipwai migrate`, then `make bootstrap` again where it stopped.

## 1.2.0 — MINOR

**The account keeps the passphrase that decrypts the committed bootstrap state.** The first `make bootstrap`
still generates one and prints it once, and the apply now keeps it as the SSM SecureString parameter
`/<project>/bootstrap/state-passphrase`. A later `make bootstrap` — after `add-service`, or from somebody
else's laptop — signed in to the account reads it back, and `TF_VAR_state_passphrase` still overrides it.
Whoever may read the parameter may decrypt the state, which is the trust the encrypted state already assumed.
The identity bootstrapping needs `ssm:PutParameter` now, and the pre-apply permission check asks for it.

**Catch-up:** `make bootstrap` once, with `TF_VAR_state_passphrase` set as before: that apply writes the
parameter, and the next run needs nothing.

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

