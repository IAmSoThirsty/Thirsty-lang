# Shipping Thirsty-Lang: Complete Docker Setup

This guide walks you through shipping your first Thirsty-Lang release as a production Docker image.

---

## What You Have Now

✓ **Dockerfile** — Multi-stage build with integrated test gate (1212 tests must pass)  
✓ **docker-compose.yml** — 9 development and testing services  
✓ **docker-quick.sh / docker-quick.bat** — One-command CLI helpers  
✓ **.github/workflows/docker.yml** — Automated GitHub Actions CI/CD  
✓ **DOCKER.md** — Complete Docker usage documentation  

---

## Release Workflow

### 1. Tag a Release

```bash
# Locally, bump your version
git tag v<version>
git push tp v<version>
```

### 2. GitHub Actions Automatically:

- Checks out your code
- Builds the Dockerfile (with all tests running inside)
- If any test fails → build fails, image doesn't ship
- If all tests pass → image is pushed to GHCR
- Generates a GitHub release summary with pull/run commands

### 3. Anyone Can Use It:

```bash
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:0.8.3 run --demo
```

---

## First Release: Step by Step

### Step 1: Make Sure Everything Works Locally

```bash
# Build the image
docker build -t thirsty-lang:test .

# Run the demo
docker run --rm thirsty-lang:test run --demo

# Run full test suite
docker compose run --rm test
```

### Step 2: Commit Docker Files

```bash
git add Dockerfile .dockerignore docker-compose.yml docker-quick.* DOCKER.md
git commit -m "chore: add Docker containerization and CI/CD pipeline"
git push tp master
```

### Step 3: Create Release Tag

```bash
git tag v<version>
git push tp v<version>
```

**That's it.** GitHub Actions takes it from here.

### Step 4: Monitor the Workflow

Visit: `https://github.com/IAmSoThirsty/Thirsty-lang/actions`

Watch the **"Build and Push Docker Image"** workflow run. It will:
- Build the image (~2-3 minutes)
- Run tests inside the build
- Push to GHCR
- Generate a release summary

---

## GHCR Access Setup (One-Time)

Your GitHub Actions workflow uses `${{ secrets.GITHUB_TOKEN }}`, which is **automatically provided** — no setup needed.

However, if you want to push images manually:

```bash
# Log in with your GitHub credentials
docker login ghcr.io -u <your-github-username> -p <your-github-token>

# Then push manually
docker push ghcr.io/iamsothirsty/thirsty-lang:0.8.3
```

---

## Verify Everything Works

After your first release, test that anyone can pull and run it:

```bash
# Pull the image (simulates what users see)
docker pull ghcr.io/iamsothirsty/thirsty-lang:latest

# Run it
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:latest --version
docker run --rm ghcr.io/iamsothirsty/thirsty-lang:latest run --demo
```

---

## Image Availability

Once pushed, your image is available at:

```
ghcr.io/iamsothirsty/thirsty-lang:0.8.3    (specific version)
ghcr.io/iamsothirsty/thirsty-lang:latest   (always latest)
```

---

## Local Development Workflow

### Change Code → Test → Release

```bash
# 1. Edit src/
vim src/utf/thirsty_lang/lexer.py

# 2. Test locally
docker compose run --rm test

# 3. Format
docker compose run --rm fmt

# 4. Commit
git add -A
git commit -m "feat: add new feature"
git push tp master

# 5. Release
git tag v<version>
git push tp v<version>

# 6. Everyone has it
docker pull ghcr.io/iamsothirsty/thirsty-lang:0.8.3
```

---

## PyPI + Docker Together

Your release workflow does **both**:

1. **PyPI** (existing workflow: `release.yml`)
   - `pip install thirsty-lang`

2. **Docker** (new workflow: `docker.yml`)
   - `docker run ghcr.io/.../thirsty-lang:latest`

Users can choose their preferred distribution.

---

## Troubleshooting

### Workflow shows "Build failed"

Check the logs: `Actions > Build and Push Docker Image > [failed job]`

Common causes:
- A test failed (intentional — no broken images ship)
- Missing Dockerfile
- GHCR registry permissions

### "Permission denied" on GHCR

The workflow uses `${{ secrets.GITHUB_TOKEN }}`, which is automatically scoped to your repo. This "just works" — no setup needed.

### Image size is large

Current: 255MB (Python 3.11-slim + thirsty-lang deps)

To reduce:
- Use `python:3.11-alpine` (~150MB, requires C toolchain in builder)
- Multi-stage strip dev deps (already done)
- Remove docs from final image

### Want to also push to Docker Hub?

Add another login step in the workflow:

```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@af1e73f918a031802d376d3c8bbc3fe56130a9b0 # v4
  with:
    registry: docker.io
    username: ${{ secrets.DOCKER_HUB_USERNAME }}
    password: ${{ secrets.DOCKER_HUB_PASSWORD }}

# Then add docker.io tags to build-push-action tags
```

---

## Next: Multi-Architecture Builds

The current workflow builds only for `linux/amd64`. To support ARM64 (M1/M2 Macs, Raspberry Pi):

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@96fe6ef7f33517b61c61be40b68a1882f3264fb8 # v4

- name: Build and push
  uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7
  with:
    platforms: linux/amd64,linux/arm64
    # ... rest of config
```

This builds for both architectures and pushes both to GHCR. Users get the right one automatically.

---

## Summary

You now have:

1. ✓ **Local development** — `docker compose run --rm dev` with hot-reload
2. ✓ **Test automation** — Tests run inside the build; broken builds don't ship
3. ✓ **Public distribution** — Tag a release, GitHub Actions builds and pushes
4. ✓ **Global access** — Anyone does `docker run ghcr.io/.../thirsty-lang:latest`
5. ✓ **PyPI + Docker** — Users pick their distribution

From source release to container release, the same commit now carries the package, Docker image, and CI evidence.
