# Dependency security and reproducible installs

Main mobile workflow now uses `npm ci`, as the existing Android job already did. `package.json` and top-level `package-lock.json` are aligned to `0.2.0`; transitive dependency package versions are unchanged.

Added isolated `.github/workflows/marina-mobile-dependency-audit.yml` for pull requests modifying manifests, manual dispatch, and weekly scheduling **after this workflow is merged to GitHub's default branch**. It runs `npm ci --ignore-scripts` and a **blocking** `npm audit --omit=dev --audit-level=moderate` for production advisories.

The previously reported `28 moderate` count has **not** been independently verified. A GitHub Actions security audit result is required; dependency upgrades will be addressed against the actual advisory IDs, not invented. Passing runtime and Jest tests does not imply a vulnerability-free dependency tree.

Production release remains BLOCKED until audit findings are reconciled and all HIGH/CRITICAL issues (if any) are fixed or explicitly justified in a signed security exception.
