# AWS Terraform stubs (committed, **not** applied)

These files exist so the future Supabase → AWS migration is a config + apply,
not a rewrite. They are intentionally minimal — provision the absolute least to
run the same container images: RDS Postgres 16, ECS Fargate for the API,
S3 + CloudFront for the web, Cognito for identity, Secrets Manager for the env.

Bring-up:

```bash
cd infra/aws
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars
```

See [`infra/runbooks/migrate-to-aws.md`](../runbooks/migrate-to-aws.md) for the
full migration playbook.

## Why these are stubs

- Region, sizing, retention defaults are placeholders — adjust per env.
- IAM is minimised but not productionised (no cross-account, no PrivateLink).
- The Terraform state backend is local; switch to S3 + DynamoDB before applying.
