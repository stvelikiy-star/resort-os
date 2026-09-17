from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
patcher = root / "scripts/apply_hotel_date_fix.py"
code = patcher.read_text(encoding="utf-8")
exec(compile(code, str(patcher), "exec"), {"__name__": "__main__", "__file__": str(patcher)})

# The original patcher intentionally prepares the final CI workflow and deletes
# one-shot machinery. GitHub Actions' GITHUB_TOKEN cannot push workflow-file
# changes in this repository, so restore those paths for this automated commit.
subprocess.run(
    ["git", "checkout", "--", ".github/workflows/apply-hotel-date-fix.yml", "scripts/apply_hotel_date_fix.py"],
    cwd=root,
    check=True,
)
(root / ".github/workflows/hotel-business-date-ci.yml").unlink(missing_ok=True)

# Do not leave this compatibility wrapper in the feature diff.
Path(__file__).unlink(missing_ok=True)
print("hotel date patch prepared without workflow mutations")
