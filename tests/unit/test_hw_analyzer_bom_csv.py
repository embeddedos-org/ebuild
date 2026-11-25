# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""BOM CSV rows must be split as CSV, honouring quoted fields.

KiCad's grouped BOM export writes every reference sharing a value into one
quoted field: ``"U3,U4,U5","BME280",...``. interpret_bom split each line on
every comma, so the references spilled across the first three columns and
the part value -- the one thing the component database is searched for --
was never looked at.
"""

from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer

_BOM = (
    "Reference,Value,Description\n"
    '"U3,U4,U5","BME280","Environmental sensor"\n'
    "U1,STM32F407VG,MCU\n"
)


def _part_names(profile):
    return [p.name for p in profile.peripherals]


def test_quoted_multi_reference_field_does_not_hide_the_part_value():
    profile = EosHardwareAnalyzer().interpret_bom(_BOM)

    assert "BME280" in _part_names(profile)
    bme = next(p for p in profile.peripherals if p.name == "BME280")
    assert bme.bus == "i2c"


def test_unquoted_rows_are_read_as_before():
    profile = EosHardwareAnalyzer().interpret_bom("U2,BME280,sensor\n")

    assert "BME280" in _part_names(profile)
