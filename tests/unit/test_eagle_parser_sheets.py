# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Eagle connects nets that share a name across the sheets of a schematic.

The parser read each sheet's <net> on its own, so a two-sheet design with
the MCU on sheet 1 and a sensor on sheet 2 came back as two "SDA" nets with
half the pins each, and neither showed the MCU and the sensor connected.
"""

from ebuild.eos_ai.eagle_parser import EagleParser

_TWO_SHEETS = """<?xml version="1.0" encoding="utf-8"?>
<eagle version="9.6.2">
  <drawing>
    <schematic>
      <parts>
        <part name="U1" library="mcu" deviceset="STM32F407" device="" value="STM32F407VG"/>
        <part name="U2" library="sensor" deviceset="BME280" device="" value="BME280"/>
        <part name="R1" library="rcl" deviceset="R" device="" value="4k7"/>
      </parts>
      <sheets>
        <sheet>
          <nets>
            <net name="SDA">
              <segment>
                <pinref part="U1" gate="G$1" pin="PB7"/>
                <pinref part="R1" gate="G$1" pin="1"/>
              </segment>
            </net>
            <net name="SCL">
              <segment>
                <pinref part="U1" gate="G$1" pin="PB6"/>
              </segment>
            </net>
          </nets>
        </sheet>
        <sheet>
          <nets>
            <net name="SDA">
              <segment>
                <pinref part="U2" gate="G$1" pin="SDI"/>
              </segment>
            </net>
            <net name="VDD">
              <segment>
                <pinref part="U2" gate="G$1" pin="VDD"/>
              </segment>
            </net>
          </nets>
        </sheet>
      </sheets>
    </schematic>
  </drawing>
</eagle>
"""


def _parse(tmp_path):
    sch = tmp_path / "board.sch"
    sch.write_text(_TWO_SHEETS, encoding="utf-8")
    result = EagleParser().parse(str(sch))
    assert result.errors == []
    return result


def test_same_named_net_on_two_sheets_is_one_net(tmp_path):
    result = _parse(tmp_path)

    assert [net.name for net in result.nets] == ["SDA", "SCL", "VDD"]
    sda = result.nets[0]
    assert [(p.part, p.pin) for p in sda.pins] == [
        ("U1", "PB7"), ("R1", "1"), ("U2", "SDI"),
    ]


def test_nets_for_a_part_include_pins_on_other_sheets(tmp_path):
    result = _parse(tmp_path)

    sensor_nets = result.get_nets_for_part("U2")
    assert [net.name for net in sensor_nets] == ["SDA", "VDD"]
    assert {p.part for p in sensor_nets[0].pins} == {"U1", "R1", "U2"}
