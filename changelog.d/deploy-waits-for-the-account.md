MINOR

**A project pushed before its account is ready keeps a green trunk.** `deploy.yml` started on every push to
`main` that passed `verify`, and failed at the sign-in until `make bootstrap` had written the repository's
variables — and a fleet's harbourmaster lands nothing while trunk is red. The pipeline now answers the
keel's optional `configured` key with `AWS_DEPLOY_ROLE_ARN`, the role every job becomes; a keel that reads it
skips the deploy, `production.yml` and `rollback.yml` whole until the variable is set, and the first push
after `make bootstrap` deploys. A keel older than the key ignores it and generates the workflows it always
did.

**Catch-up:** run `slipwai migrate` in a project generated for AWS and commit the workflow files it
rewrites.
