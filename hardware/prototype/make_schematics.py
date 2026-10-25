#!/usr/bin/env python3
"""!
@file make_schematics.py
@brief Draws the prototype schematics (D1 mini + HiLetgo MAX3232 module, and the battery
       option) as SVG and PNG with schemdraw.
@details The prototype is built from modules and through-hole parts so it behaves like the
         rs232-shield rev 0.3 (NOTES I-21, I-22, I-24). Each circuit is drawn on its own with
         net names (D1, D2, VSW, DET, ...) instead of one tangle of wires; nets with the same
         name are connected. Module-to-module wiring is in README.md.
         - A: Q1 (PNP) switches the MAX3232 module's supply (low on D1 = on), as FORCEOFF
           does on the TRS3243E.
         - B: Q2 (NPN, common base) sees a console's idle negative TxD and pulls DET low,
           standing in for the TRS3243E INVALID pin (here low = console seen).
         - C: Q3 (PNP) lights the yellow LED only while the chip is on AND a console is seen.
         - D: D0 drives the green state LED, as on the shield.
         - Sheet 2: TP4056 USB-C charger module with protection, switch in the battery
           branch only, Schottky diodes standing in for the shield's diode and P-FET,
           battery level on A0.
         Usage: python3 make_schematics.py   (writes prototype-*.svg/png next to this file)
"""
import os
import subprocess

import schemdraw
import schemdraw.elements as elm

HERE = os.path.dirname(os.path.abspath(__file__))  ##< Output folder.


def save(d, name):
    """!
    @brief Save a drawing as SVG and, with rsvg-convert, as PNG.
    @param d Drawing.
    @param name File stem.
    """
    svg = os.path.join(HERE, name + ".svg")
    d.save(svg)
    try:
        subprocess.run(["rsvg-convert", "-d", "150", "-p", "150", "-b", "white", svg, "-o",
                        os.path.join(HERE, name + ".png")], check=True)
    except (OSError, subprocess.CalledProcessError):
        print("rsvg-convert failed; SVG only")


def net(name, loc="left"):
    """! @brief Open-dot net label at the current position. @param name Net. @param loc Side. """
    elm.Dot(open=True)
    elm.Label().label(name, loc=loc, ofst=0.15)


def title(x, y, text):
    """! @brief Heading at (x, y). """
    elm.Label().at((x, y)).label(text, fontsize=13, halign="left")


def circuit_a(d, x, y):
    """! @brief A: module supply switch. D1 low = module on; R2 keeps it off through reset. """
    title(x - 1.0, y + 4.6, "A  RS-232 module power (D1 low = on)")
    elm.Dot(open=True).at((x, y))
    elm.Label().at((x, y)).label("D1", loc="left", ofst=0.15)
    elm.Resistor().at((x, y)).right().label("R1 1k", loc="top")
    q1 = elm.BjtPnp(circle=True).anchor("base").right().label("Q1\n2N3906", loc="right", ofst=(0.3, 0))
    elm.Line().at(q1.emitter).up(1.0)
    top = d.here
    elm.Vdd().label("3V3")
    elm.Line().at(top).left(0.9)
    elm.Resistor().down().toy(q1.base).label("R2\n10k", loc="bottom")
    elm.Dot()
    elm.Line().at(q1.collector).down(0.8)
    elm.Line().right(0.6)
    net("VSW (module VCC)", loc="right")


def circuit_b(d, x, y):
    """! @brief B: cable detect. Console idle TxD (-5..-12 V) turns Q2 on, so DET goes low. """
    title(x - 1.0, y + 4.6, "B  Cable detect (DET low = console seen)")
    elm.Dot(open=True).at((x, y))
    elm.Label().at((x, y)).label("CON_TXD\n(MAX3232 pin 13,\nR1IN)", loc="left", ofst=0.15)
    elm.Resistor().at((x, y)).right().label("R4 10k", loc="top")
    elm.Diode().right().reverse().label("D3 1N4148", loc="top")
    q2 = elm.BjtNpn(circle=True).anchor("emitter").up().flip().label("Q2\n2N3904", loc="right", ofst=(0.3, 0))
    elm.Line().at(q2.base).right(0.6)
    elm.Ground()
    elm.Line().at(q2.collector).up(0.6)
    det = d.here
    elm.Dot()
    elm.Resistor().up().label("R5 47k", loc="bottom")
    elm.Vdd().label("3V3")
    elm.Line().at(det).right(2.2)
    elm.Dot()
    cap = d.here
    elm.Capacitor().down().label("C1 1uF", loc="bottom")
    elm.Ground()
    elm.Line().at(cap).right(1.0)
    net("DET (to D2)", loc="right")


def circuit_c(d, x, y):
    """! @brief C: yellow LED = chip on AND console seen. Q3 needs VSW high and DET low. """
    title(x - 1.0, y + 4.6, "C  Yellow LED: chip on AND console seen")
    elm.Dot(open=True).at((x, y))
    elm.Label().at((x, y)).label("DET", loc="left", ofst=0.15)
    elm.Resistor().at((x, y)).right().label("R6 22k", loc="top")
    q3 = elm.BjtPnp(circle=True).anchor("base").right().label("Q3\n2N3906", loc="right", ofst=(0.3, 0))
    elm.Line().at(q3.emitter).up(0.8)
    net("VSW", loc="right")
    elm.Line().at(q3.collector).down(0.4)
    elm.Resistor().down().label("R7 330", loc="bottom")
    elm.LED().down().label("LED1\nyellow", loc="bottom")
    elm.Ground()


def circuit_d(d, x, y):
    """! @brief D: green state LED on D0, driven by firmware. """
    title(x - 1.0, y + 4.6, "D  Green state LED (firmware)")
    elm.Dot(open=True).at((x, y))
    elm.Label().at((x, y)).label("D0", loc="left", ofst=0.15)
    elm.Resistor().at((x, y)).right().label("R8 330", loc="top")
    elm.LED().down().label("LED2\ngreen", loc="bottom")
    elm.Ground()


def sheet_core():
    """! @brief Sheet 1: the four circuits added around the D1 mini and MAX3232 module. """
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=11, unit=2.2)
        elm.Label().at((-1, 6.5)).label(
            "WiFi Terminal prototype, sheet 1: circuits around the D1 mini and HiLetgo MAX3232 module",
            fontsize=15, halign="left")
        elm.Label().at((-1, 5.7)).label(
            "Nets with the same name are connected. Module wiring: README.md. 3V3 = D1 mini 3V3 pin.",
            fontsize=10, halign="left")
        circuit_a(d, 2.0, 0)
        circuit_b(d, 19.0, 0)
        circuit_c(d, 2.0, -11)
        circuit_d(d, 19.0, -11)
        save(d, "prototype-sheet1-core")


def sheet_battery():
    """! @brief Sheet 2: battery option with a TP4056 USB-C charger module. """
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=11, unit=2.2)
        elm.Label().at((-2, 6.5)).label("WiFi Terminal prototype, sheet 2: battery option", fontsize=15,
                                        halign="left")
        elm.Label().at((-2, 5.7)).label(
            "Without the battery option, leave all of this off and power the D1 mini from its USB.",
            fontsize=10, halign="left")
        tp = d.add(elm.Ic(pins=[
            elm.IcPin(name="IN-", side="left", anchorname="INN"),   # first listed = bottom
            elm.IcPin(name="IN+", side="left", anchorname="INP"),
            elm.IcPin(name="OUT-", side="right", anchorname="OUTN"),
            elm.IcPin(name="OUT+", side="right", anchorname="OUTP"),
            elm.IcPin(name="B-", side="bottom", anchorname="BN"),
            elm.IcPin(name="B+", side="bottom", anchorname="BP"),
        ], edgepadW=3.6, edgepadH=1.0, pinspacing=1.8,
            label="TP4056 USB-C\ncharger module\nwith protection\n(its USB-C is the\nunit's charge and\npower port)",
            lblsize=10).at((4, 0)))
        # Cell between B+ and B-
        elm.Line().at(tp.BP).down(2.0)
        elm.BatteryCell().left().tox(tp.BN[0]).label("LiPo 3.7 V, + to B+", loc="bottom", ofst=0.4)
        elm.Line().up().toy(tp.BN)
        # USB path: IN+ -> D4 -> SYS
        elm.Line().at(tp.INP).left(0.8)
        elm.Line().up(2.2)
        elm.Diode().right().label("D4 1N5817 (USB path)", loc="top")
        elm.Line().right().tox(tp.OUTP[0] + 9.0)
        elm.Dot()
        sysn = d.here
        elm.Line().right(1.0)
        net("D1 mini 5V pin", loc="right")
        elm.Line().at(tp.INN).left(0.3)
        elm.Label().label("IN-: no other connection\n(it is B-, before the\nprotection switch)", loc="left",
                          fontsize=9)
        # Battery path: OUT+ -> SW1 -> D5 -> SYS
        elm.Line().at(tp.OUTP).right(1.0)
        elm.Dot()
        outp = d.here
        elm.Switch().right().label("SW1 power", loc="top")
        elm.Diode().right().label("D5 1N5817 (*)", loc="top")
        elm.Line().up().toy(sysn)
        # Battery level: OUT+ -> R9 -> A0
        elm.Line().at(outp).down(1.6)
        elm.Resistor().right().label("R9 100k", loc="top")
        elm.Line().right(0.8)
        net("D1 mini A0", loc="right")
        # Ground from OUT-
        elm.Line().at(tp.OUTN).right(0.6)
        elm.Line().down(4.2)
        elm.Line().right(5.0)
        net("D1 mini GND", loc="right")
        elm.Label().at((-2, -6.8)).label(
            "(*) D5 stands in for the shield's P-FET (0.3 V drop). D4 = the shield's USB diode. "
            "SW1 only matters on battery: with USB in, the unit runs and charges.",
            fontsize=10, halign="left")
        save(d, "prototype-sheet2-battery")


if __name__ == "__main__":
    sheet_core()
    sheet_battery()
