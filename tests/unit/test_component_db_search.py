# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""ComponentDB.search must find parts written with their usual hyphen.

Database keys are normalised (lower-case, punctuation removed), so
``MPU6050`` is stored as ``mpu6050``. search() only lower-cased the text it
scanned, so the standard spellings ``MPU-6050``, ``ICM-20948``, ``NEO-6M``
and ``HC-SR04`` never matched, and the analyzer reported no peripheral for
them from a BOM, schematic or description.
"""

import pytest

from ebuild.eos_ai.component_db import ComponentDB


@pytest.mark.parametrize("text, part", [
    ("U4 MPU-6050 6-axis IMU", "MPU6050"),
    ("ICM-20948", "ICM20948"),
    ("u-blox NEO-6M GPS module", "NEO6M"),
    ("HC-SR04 ultrasonic ranger", "HCSR04"),
    ("ESP_01 Wi-Fi module", "ESP01"),
])
def test_hyphenated_part_numbers_are_found(text, part):
    assert part in [info.part for info in ComponentDB().search(text)]


def test_plain_spelling_and_unrelated_text_are_unchanged():
    db = ComponentDB()

    assert [info.part for info in db.search("TMP102 on I2C")] == ["TMP102"]
    assert db.search("10k resistor, 100nF capacitor") == []
