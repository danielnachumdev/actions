# Example: Python uv library

## Wire-up

1. Copy [`templates/workflows/ci.yml`](../../templates/workflows/ci.yml) → `.github/workflows/ci.yml`  
2. Copy [`templates/workflows/cd.yml`](../../templates/workflows/cd.yml) → `.github/workflows/cd.yml`  
3. Copy CODEOWNERS + dependabot from [`templates/github/`](../../templates/github/)  
4. Labels: `bumpMajor`, `bumpMinor`, `bumpPatch`, `noBump`, `dependencies`  
5. Required checks: **`CI / CI`**, **`Label / Label`**  
6. Pin `@v1`

## Pins

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/label.yml@v1
uses: danielnachumdev/actions/.github/workflows/release.yml@v1
```

## Reference

[gp_wrapper](https://github.com/danielnachumdev/gp_wrapper) — first library consumer.
