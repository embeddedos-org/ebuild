# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

#!/usr/bin/env python3
"""
EoSuite GUI — Entry point.
Launch the graphical interface for EoSuite multi-tool terminal suite.
"""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
