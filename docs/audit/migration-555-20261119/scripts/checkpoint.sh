#!/usr/bin/env bash
# Compare the two tracked working trees with the immutable commits.
set -eu
for version in old new; do
  git -C "$version" rev-parse HEAD
  git -C "$version" diff --exit-code HEAD --
done
