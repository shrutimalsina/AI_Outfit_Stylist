# Production handoff

## Accounts and access

| Account or service | When needed | What to provide |
| --- | --- | --- |
| GitHub | Already set up for the project repository and Actions | Nothing new for the current repository |
| Hugging Face | Downloading the gated Polyvore dataset | Request access on the authors' dataset page. Use a read token authorized for gated repositories in the terminal login prompt. Report whether access was granted. |
| Hosting provider or university server | Public deployment | Share the provider or university, server hostname or public IP, SSH username, and whether Docker Compose and persistent storage are available. |
| DNS provider or domain registrar | Public HTTPS if the host does not supply a usable hostname | Share the desired public hostname and confirm you can manage its DNS. An existing domain or university hostname is sufficient. |

Keep tokens, passwords, cloud keys, SSH private keys, and .env contents out
of chat and Git. For server access, use an existing SSH key or add its public
half to the server through the provider. Test with `ssh USER@HOST` in a terminal.
PostgreSQL runs in Compose, and CLIP runs on the host. Neither requires a
managed database or paid inference account. The local seminar demo requires
no hosting or DNS account.

## Workstation preparation

From the project root, run:

```sh
bash scripts/check_environment.sh
bash scripts/bootstrap.sh
bash scripts/run_tests.sh
```

To run the synthetic demo, use `bash scripts/run_demo.sh` and run
`npm --prefix frontend run dev` in a second terminal.

After Hugging Face grants dataset access:

```sh
.venv/bin/hf auth login
.venv/bin/python -m pipeline.acquire_dataset
```

Inspect the archive schema and continue through unpacking, ingestion, embedding
extraction, validation evaluation and the final test using the [README](../README.md).

## Production host preparation

Install Docker with Compose on the chosen host. Clone the project, arrange
persistent storage and configure HTTPS at the host proxy. Allow inbound HTTPS
and whichever certificate validation ports the proxy needs. Keep the application
and database on their existing private bindings.

Generate the PostgreSQL password once on the host with
`bash scripts/init_production_env.sh`. This writes a private .env and refuses
to overwrite an existing one. Use the existing password for an existing
database volume. Configure the desired hostname in DNS and the TLS proxy.

Transfer the manifest, snapshot, images, and model cache following the
[deployment runbook](deployment.md). Copy the cache's `hub` directory only,
leaving account credentials on the workstation. Use `scripts.release_preflight`
with the real release before startup. After startup, verify readiness and
a sample recommendation through the public HTTPS URL.

For the next handoff, send the access status, host or provider, public IP or
hostname, SSH username, and desired public URL. Local-only is also a valid
choice for the seminar.
