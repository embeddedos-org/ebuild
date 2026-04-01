# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""ebuild EoS AI module — AI-assisted hardware analysis and build orchestration.

Analyzes hardware design docs, schematics, BOMs, and datasheets to generate
validated build configs for eos (OS) and eboot (bootloader) projects.
Works offline with built-in rule engine. Optional LLM backend for advanced analysis.
"""

# Always available — no external dependencies
from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer

# Always available — no external dependencies beyond eos_hw_analyzer
from ebuild.eos_ai.eos_project_generator import EosProjectGenerator

# Always available — component database and parsers
from ebuild.eos_ai.component_db import ComponentDB
from ebuild.eos_ai.kicad_parser import KiCadParser
from ebuild.eos_ai.eagle_parser import EagleParser
from ebuild.eos_ai.llm_integration import LLMClient

# Requires pyyaml — lazy import to allow tests without yaml installed
try:
    from ebuild.eos_ai.eos_config_generator import EosConfigGenerator
    from ebuild.eos_ai.eos_validator import EosConfigValidator
    from ebuild.eos_ai.eos_boot_integrator import EosBootIntegrator
except ImportError:
    EosConfigGenerator = None
    EosConfigValidator = None
    EosBootIntegrator = None

__all__ = [
    "EosHardwareAnalyzer",
    "EosProjectGenerator",
    "EosConfigGenerator",
    "EosConfigValidator",
    "EosBootIntegrator",
    "ComponentDB",
    "KiCadParser",
    "EagleParser",
    "LLMClient",
]
