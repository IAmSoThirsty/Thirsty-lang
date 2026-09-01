# Thirsty-Lang Docker Guide

## Current Published Image

The authoritative container for Thirsty-Lang 0.8.6 is:

```text
ghcr.io/iamsothirsty/thirsty-lang:0.8.6
```

It is a multi-architecture image for `linux/amd64` and `linux/arm64`. The
published manifest is anchored by this digest:

```text
sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c
```

The v0.8.6 Docker workflow completed successfully in GitHub Actions run
`30756676576`.

> Docker Hub is not a current distribution channel. Its `latest` and `0.8.1`
> tags are historical and unmaintained. Do not use
> `thirstyoftp/thirsty-lang` when validating or deploying 0.8.6.

Prefer the immutable version tag for normal use. For the strongest artifact
pin, use the manifest digest:

```bash
docker pull ghcr.io/iamsothirsty/thirsty-lang:0.8.6
docker pull ghcr.io/iamsothirsty/thirsty-lang@sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c
```

## Quick Start

### Verify the CLI and run the demo

```bash
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:0.8.6 --version
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:0.8.6 run --demo
```

### Start an interactive REPL

```bash
docker run -it --rm ghcr.io/iamsothirsty/thirsty-lang:0.8.6 repl
```

### Run a script from the current directory

macOS/Linux:

```bash
docker run --rm -v "$(pwd):/work" \
  ghcr.io/iamsothirsty/thirsty-lang:0.8.6 \
  run /work/myfile.thirsty
```

PowerShell:

```powershell
docker run --rm -v "${PWD}:/work" `
  ghcr.io/iamsothirsty/thirsty-lang:0.8.6 `
  run /work/myfile.thirsty
```

## Local Development

Build a local image without publishing it:

```bash
docker build -t thirsty-lang:dev .
```

Run the full test service:

```bash
docker compose run --rm test
```

Open the development shell with the repository source mounted:

```bash
docker compose run --rm dev
```

Format the project or run its health check:

```bash
docker compose run --rm fmt
docker compose run --rm doctor
```

## Docker Compose Services

`docker-compose.yml` defines exactly eight services:

| Service | Purpose |
| --- | --- |
| `repl` | Interactive Thirsty-Lang REPL |
| `test` | Full Python test suite |
| `thirsty` | Execute the `thirsty` CLI |
| `build-js` | Compile a Thirsty-Lang source file to JavaScript |
| `dev` | Development shell with mounted source |
| `doctor` | Project health check |
| `fmt` | Source formatter |
| `lsp` | TARL language server on port 9898 |

List the services from the active Compose configuration:

```bash
docker compose config --services
```

Run any service with:

```bash
docker compose run --rm <service>
```

## Image Contents

The runtime image is based on `python:3.11-slim`, runs as the non-root
`thirsty` user with UID 1000, and uses the `thirsty` CLI as its entrypoint.
It includes all seven installed command-line entry points:

- `thirsty` - core and governed runtime, build, proof, audit, and tooling
- `thirst-of-gods` - divine contract validation
- `tarl` - policy evaluation, proof verification, and audit tools
- `shadow-thirst` - mutation and invariant analysis
- `tscg` - symbolic constraint grammar tools
- `tscg-b` - binary frame protocol tools
- `tarl-lsp` - TARL Language Server Protocol server

## Governance Example

Mount the program, policy, and context schema into the container and invoke the
governed runtime explicitly:

```bash
docker run --rm -v "$(pwd):/work" \
  ghcr.io/iamsothirsty/thirsty-lang:0.8.6 \
  run /work/program.thirsty \
  --thirst-level governed \
  --policy /work/policy.tarl \
  --context-schema /work/context.schema.json \
  --authority myapp
```

For a load-bearing deployment, also follow the context, proof, key,
freshness, replay, and revocation requirements documented in `README.md`,
`docs/THREAT_MODEL.md`, and `docs/STATUS.md`.

## Release Publishing

The Docker workflow is defined in `.github/workflows/docker.yml` and supports:

- `v*` tags for a coordinated PyPI and container release;
- `docker-v*` tags for a Docker-only publication; and
- manual workflow dispatch for an explicitly supplied version.

Every published workflow build targets `linux/amd64` and `linux/arm64`. The
Dockerfile runs the test suite before constructing the runtime stage. The
workflow then pulls the GHCR image and runs both `--version` and `run --demo`.

For a normal versioned release:

```bash
git tag -a v<version> -m "Thirsty-Lang <version>"
git push tp refs/tags/v<version>
```

For a Docker-only rebuild of an already released source state:

```bash
git tag -a docker-v<version> -m "Thirsty-Lang Docker <version>"
git push tp refs/tags/docker-v<version>
```

Do not publish from an unverified working tree. Complete the checklist in
`SHIPPING.md` before creating either tag.

Docker Hub publication is conditional on repository secrets. It is not part of
the verified 0.8.6 distribution and should remain undocumented as a current
consumer endpoint until its versioned and `latest` tags are rebuilt and
independently verified.

## Local Helper Scripts

macOS/Linux:

```bash
bash docker-quick.sh build
bash docker-quick.sh run --demo
bash docker-quick.sh repl
bash docker-quick.sh test
bash docker-quick.sh dev
bash docker-quick.sh fmt
bash docker-quick.sh doctor
bash docker-quick.sh version
```

Windows:

```bat
docker-quick.bat build
docker-quick.bat run --demo
docker-quick.bat repl
docker-quick.bat test
docker-quick.bat dev
docker-quick.bat fmt
docker-quick.bat doctor
docker-quick.bat version
```

The helper scripts also expose a local cleanup command. Review the targeted
Docker objects before using it on a machine with other active image work.

## Troubleshooting

### Image not found

Confirm the GHCR path and explicit version:

```bash
docker pull ghcr.io/iamsothirsty/thirsty-lang:0.8.6
```

Do not substitute the stale Docker Hub image.

### Build fails while running tests

The Dockerfile has a test gate in its builder stage. A failing test prevents
the runtime image from being built. Run the same suite with:

```bash
docker compose run --rm test
```

### Mounted files are not writable

The runtime image intentionally runs as `thirsty:1000`. Ensure the mounted
directory permits access by that UID, or use the development service appropriate
for your host.

### Confirm the published architectures

```bash
docker buildx imagetools inspect ghcr.io/iamsothirsty/thirsty-lang:0.8.6
```

The manifest must list both `linux/amd64` and `linux/arm64` before it is
described as the current multi-architecture release.
