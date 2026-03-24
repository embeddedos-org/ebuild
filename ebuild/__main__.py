"""Allow running ebuild as a module: python -m ebuild."""

from ebuild.cli.commands import cli

if __name__ == "__main__":
    cli()
