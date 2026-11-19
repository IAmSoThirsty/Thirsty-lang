# Thirsty-Lang Docker Guide

## Preserved 0.8.6 Image Evidence

The image and digest below identify the previously verified Thirsty-Lang 0.8.6
container. Version 0.9.1 ships as a Python wheel and source distribution.
To run 0.9.1 in a container, build the Dockerfile from the `pypi-v0.9.1` tag.

```text
ghcr.io/iamsothirsty/thirsty-lang:0.8.6
```

The recorded multi-architecture image covers `linux/amd64` and `linux/arm64`.
Its recorded manifest digest is:

```text
sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c
```

The v0.8.6 Docker workflow completed successfully in GitHub Actions run
`30756676576`.

The preserved release record did not verify Docker Hub as a distribution
channel. It does not establish the present contents of any mutable `latest` tag.

To reproduce that historical artifact, use its manifest digest rather than
assuming a tag still identifies the same bytes:

```bash
docker pull ghcr.io/iamsothirsty/thirsty-lang:0.8.6
docker pull ghcr.io/iamsothirsty/thirsty-lang@sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c
```

## Quick Start

Build the current source as a local development image. These examples do not
publish an image or verify a remote release:

```bash
docker build -t thirsty-lang:dev .
```

### Verify the CLI and run the demo

```bash
docker run --rm thirsty-lang:dev --version
docker run --rm thirsty-lang:dev run --demo
```

### Start an interactive REPL

```bash
docker run -it --rm thirsty-lang:dev repl
```

### Run a script from the current directory

macOS/Linux:

```bash
docker run --rm -v "$(pwd):/work:ro" \
  thirsty-lang:dev \
  run /work/myfile.thirsty
```

PowerShell:

```powershell
docker run --rm -v "${PWD}:/work:ro" `
  thirsty-lang:dev `
  run /work/myfile.thirsty
```

Programs with imports or mediated effects also need the policy and authority
shown in the governance example below. A `core` source header cannot disable
the default gate. The CLI's own prompt, diagnostics, and final result display
do not grant the program permission to use `print`, `pour`, or `sip`.

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
| `build-js` | Compile the scalar fixture with explicit governance-loss acknowledgement and a mandatory disclosure manifest |
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

- `thirsty` - governance-default runtime, explicit core compatibility, build, proof, and tooling
- `thirst-of-gods` - divine contract validation
- `tarl` - policy evaluation, proof verification, and audit tools
- `shadow-thirst` - mutation and invariant analysis
- `tscg` - symbolic constraint grammar tools
- `tscg-b` - binary frame protocol tools
- `tarl-lsp` - TARL Language Server Protocol server

## Governance Example

Mount the program, policy, and context schema into the container. The current
runtime requires governance by default:

```bash
docker run --rm -v "$(pwd):/work:ro" \
  thirsty-lang:dev \
  run /work/program.thirsty \
  --policy /work/policy.tarl \
  --context-schema /work/context.schema.json \
  --authority myapp
```

`core`, `strict`, and `pure` headers choose language semantics, not authority.
Pure effects remain prohibited through aliases and cascade callbacks, and
definitions retain their restrictions after interpreter reuse. Calling and
defining policies must both permit governed calls and mediated effects; live
credential revalidation cannot replace a binding after it has been checked.
Every shipped stdlib export has an explicit effect classification, and import
permission alone does not allow its sensitive operations.

An intentionally ungoverned compatibility run must opt out explicitly:

```bash
docker run --rm -v "$(pwd):/work:ro" thirsty-lang:dev \
  run /work/compatibility.thirsty --unsafe-core
```

That opt-out cannot be combined with the CLI's policy, authority, lock, hardened,
or audit controls. An explicit governed source declaration retains its gate.
Embedding hosts use `Interpreter(allow_ungoverned=True)` for the corresponding
explicit compatibility choice.

Public executable builds require `--allow-governance-loss` even for headerless
or `core` source. The build writes its mandatory disclosure manifest before the
executable artifact or native toolchain invocation. Compose's `build-js` service
selects this disclosed loss explicitly; the manifest is not a runtime policy
gate. Containers and language mediation alone do not prove complete resource
containment or source provenance for arbitrary foreign closures.

For a load-bearing deployment, also follow the context, proof, key,
freshness, replay, and revocation requirements documented in `README.md`,
`docs/THREAT_MODEL.md`, and `docs/STATUS.md`.

## Release Publishing

The Docker workflow is defined in `.github/workflows/docker.yml` and supports:

- `v*` tags for a coordinated PyPI and container release;
- `docker-v*` tags for a Docker-only publication; and
- manual workflow dispatch for an explicitly supplied version.

The configured workflow targets `linux/amd64` and `linux/arm64`. The
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

Docker Hub publication is conditional on repository secrets. The preserved
0.8.6 record does not verify that channel. Current publication and artifact
identity require separate release verification.

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

For the current development examples, build the local tag first:

```bash
docker build -t thirsty-lang:dev .
```

For a released image, use the version and digest established by that release's
verification record.

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

### Reinspect the historical image architectures

```bash
docker buildx imagetools inspect ghcr.io/iamsothirsty/thirsty-lang:0.8.6
```

This command concerns the historical tag. A current release needs its own
verified manifest and runtime checks; this guide does not claim they have run.
