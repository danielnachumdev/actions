# Example: Python uv library

1. Copy [`templates/workflows/ci.yml`](../../templates/workflows/ci.yml) and [`cd.yml`](../../templates/workflows/cd.yml)  
2. Copy [`templates/github/`](../../templates/github/)  
3. Labels: `noBump`, `bumpPatch`, `bumpMinor`, `bumpMajor`, `dependencies`  
4. Required checks: **`CI / CI`**, **`Semver / Semver`**  
5. Pin `@v1`

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
```

Reference: [gp_wrapper](https://github.com/danielnachumdev/gp_wrapper).
