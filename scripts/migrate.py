"""Apply non-destructive Alembic upgrades."""

import subprocess

subprocess.run(["alembic", "upgrade", "head"], check=True)
