# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Allow running ebuild as a module: python -m ebuild."""
# The integration commands are registered on the group inside
# ebuild.cli.commands, so `python -m ebuild` and the installed `ebuild`
# console script expose the same command set. Importing `cli` is enough.
from ebuild.cli.commands import cli

if __name__ == "__main__":
    cli()
