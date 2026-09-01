# Shipping Thirsty-Lang

This is the operational release guide for the Thirsty-Lang Python package and
container image. It describes the current v0.8.6 state and the checklist for a
future release.

## Current Release Receipt: v0.8.6

The authoritative container is:

```text
ghcr.io/iamsothirsty/thirsty-lang:0.8.6
```

- Architectures: `linux/amd64`, `linux/arm64`
- Manifest digest:
  `sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c`
- Successful Docker workflow run: `30756676576`

Docker Hub is not a current release endpoint. Its `latest` and `0.8.1` tags are
historical and unmaintained. Release instructions and acceptance checks must use
GHCR unless Docker Hub has been rebuilt at the same source revision and
verified separately.

## Release Surfaces

The repository has two tag-triggered workflows:

1. `.github/workflows/release.yml` validates and publishes the Python package
   to PyPI for a lowercase `v*` tag.
2. `.github/workflows/docker.yml` builds, publishes, pulls, and smoke-tests the
   multi-architecture container for `v*` tags. It also accepts `docker-v*` tags
   for a container-only publication.

The authoritative container registry is GHCR. Docker Hub upload is conditional
on repository secrets and was not part of the verified 0.8.6 release.

## Future Release Checklist

### 1. Prepare the release commit

- Confirm the intended version is consistent in package metadata, runtime
  version reporting, Docker metadata, changelog, and documentation.
- Review `git status` and preserve all unrelated local work.
- Run the repository's Python quality and test gates.
- Build the distribution and inspect its contents.
- Build the Docker image locally; run its version and demo smoke tests.
- Confirm `docker compose config --services` lists exactly these eight services:
  `repl`, `test`, `thirsty`, `build-js`, `dev`, `doctor`, `fmt`, and `lsp`.
- Commit and push the cohesive release state to the release branch.
- Wait for branch CI to pass before tagging.

Representative local container checks:

```bash
docker build -t thirsty-lang:release-candidate .
docker run --rm thirsty-lang:release-candidate --version
docker run --rm thirsty-lang:release-candidate run --demo
docker compose config --services
docker compose run --rm test
```

### 2. Create and push the annotated release tag

Only tag the exact commit that passed the pre-release gates:

```bash
git tag -a v<version> -m "Thirsty-Lang <version>"
git show --no-patch --decorate v<version>
git push tp refs/tags/v<version>
```

Pushing a lowercase `v*` tag starts both the PyPI and Docker release workflows.
Use a `docker-v*` tag only when an already selected source revision needs a
container-only publication:

```bash
git tag -a docker-v<version> -m "Thirsty-Lang Docker <version>"
git push tp refs/tags/docker-v<version>
```

### 3. Monitor both workflows

Open the repository Actions page:

```text
https://github.com/IAmSoThirsty/Thirsty-lang/actions
```

For a normal `v*` release, do not call the release complete until:

- the release workflow validates the distribution and publishes to PyPI;
- the Docker workflow builds both architectures and pushes to GHCR;
- the Docker workflow's pull, `--version`, and demo checks pass; and
- the tag resolves to the intended release commit locally and remotely.

If a workflow fails, diagnose and repair the failed gate. Do not move or reuse
the released tag to hide a different source revision.

### 4. Verify the published Python package

Use a fresh Python 3.11 environment so the check cannot import the local tree:

```bash
python -m venv .release-verify
. .release-verify/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-cache-dir thirsty-lang==<version>
python -m pip show thirsty-lang
python -c "import importlib.metadata as m; print(m.version('thirsty-lang'))"
thirsty --version
tarl --help
```

On PowerShell, activate with:

```powershell
.\.release-verify\Scripts\Activate.ps1
```

Run the release-specific security and behavior matrix in that isolated
environment. Repository tests alone do not prove the artifact downloaded from
PyPI contains the same behavior.

### 5. Verify the published container

Pull and exercise the versioned GHCR image:

```bash
docker pull ghcr.io/iamsothirsty/thirsty-lang:<version>
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:<version> --version
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:<version> run --demo
docker buildx imagetools inspect ghcr.io/iamsothirsty/thirsty-lang:<version>
```

Record the manifest-list digest and confirm the inspection includes both
`linux/amd64` and `linux/arm64`. A local single-platform build is not evidence
for the published multi-architecture manifest.

### 6. Record the release evidence

Preserve at least:

- release commit SHA and annotated tag object SHA;
- branch CI, PyPI release, and Docker workflow run IDs and conclusions;
- PyPI version and fresh-install smoke output;
- GHCR version tag, manifest digest, and architecture list;
- release-specific regression output;
- unresolved competence-register or security findings.

Update the README, changelog, status, threat model, deployment guide, and
continuity record when the release changes a documented contract.

## Local Development Cycle

For normal code changes before release:

```bash
docker compose run --rm fmt
docker compose run --rm test
docker compose run --rm doctor
```

The Compose configuration provides eight services:

- `repl`
- `test`
- `thirsty`
- `build-js`
- `dev`
- `doctor`
- `fmt`
- `lsp`

See `DOCKER.md` for individual service examples and volume-mount guidance.

## Registry Authentication

The Docker GitHub Actions workflow uses the repository-provided
`${{ secrets.GITHUB_TOKEN }}` for GHCR. A manual GHCR push requires a GitHub
token with appropriate package permissions:

```bash
docker login ghcr.io -u <github-username>
```

Do not place tokens on the command line or in documentation. Enter the token at
the prompt or pass it through a protected standard-input workflow.

The current PyPI workflow uses the scoped `IAMSOTHIRSTY` repository environment
secret. Treat a missing, expired, or unauthorized secret as a release blocker;
do not bypass the publish gate.

## Failure Handling

### Docker build fails in the test stage

The Dockerfile intentionally runs the full test suite in its builder stage. Run
the failing test locally, repair or explicitly classify the failure, and create
a new release commit before tagging.

### GHCR login or push is denied

Check repository package permissions and the workflow's `packages: write`
permission. Confirm the job is running in the intended repository and that the
package namespace matches the repository owner.

### Only one architecture is present

The release is incomplete. The workflow must publish a manifest for both
`linux/amd64` and `linux/arm64`; inspect the QEMU, Buildx, and build-push steps
before retrying from a new eligible tag or an explicitly governed Docker-only
tag.

### Docker Hub appears newer or older than GHCR

Ignore Docker Hub for the current release. Its tags are historical until a
future release explicitly publishes and verifies them alongside GHCR. Never
infer artifact equivalence from a shared version label alone.

## v0.8.6 Consumer Verification

The following commands verify the currently documented image:

```bash
docker pull ghcr.io/iamsothirsty/thirsty-lang:0.8.6
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:0.8.6 --version
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:0.8.6 run --demo
docker buildx imagetools inspect ghcr.io/iamsothirsty/thirsty-lang:0.8.6
```

Expected release identity:

```text
version: 0.8.6
manifest digest: sha256:6f3f516b8e979437dd414373afe581716b8c890dc4758b8675cbbcad9b94b13c
platforms: linux/amd64, linux/arm64
workflow run: 30756676576 (success)
```
