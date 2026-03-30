# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Allow running ebuild as a module: python -m ebuild."""
from ebuild.cli.commands import cli
from ebuild.cli.integration import register_commands

register_commands(cli)

if __name__ == "__main__":
    cli()