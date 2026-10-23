# -*- coding: utf-8 -*-
"""
TVAM printing with the Delta ECM-E3M-C20602RSE motor + ASD-E3-0221-L drive
and the ViALUX V-7000 DMD.

How the synchronisation works
    drive OA output  -> one pulse per DMD frame (P1.046 = frames per turn)
    drive Z output   -> once per turn, marks angle 0
    Arduino (arduino_servo_trigger.ino) waits for Z, then passes OA to the
    DMD trigger input and stops after exactly num_turns * frames_per_turn frames.
So the DMD stays locked to the motor *position*, like with the Zaber stage.

Each pattern is shown as K frames (--subframes), so
frames per turn = number of patterns * K.

One-time drive setup (writes the control mode, then power-cycle the drive):
    python tvam_code_servo.py --setup_drive --port_drive COM5

Wiring self-check (no DMD, no patterns needed):
    python tvam_code_servo.py --check_only --frames_per_rev 8192 -v 360 --check_turns 10

Typical print:
    python tvam_code_servo.py -p .\\images_line\\ -K 16 -v 360 -n 10 -a 12 -ph 70 --flip_vertical

Extra Python packages: pip install minimalmodbus pyserial
"""

import argparse
import sys
import time
import types

import numpy as np
import tqdm

from ALP4 import *


# tvam_code.py imports the Zaber library at the top. We only borrow its image
# loader, so provide an empty stand-in when the Zaber library is not installed.
try:
    import zaber_motion  # noqa: F401
except ImportError:
    _zm = types.ModuleType("zaber_motion")
    _zm.Units = None
    _zm_ascii = types.ModuleType("zaber_motion.ascii")
    _zm_ascii.Connection = None
    _zm_ascii.WarningFlags = None
    _zm.ascii = _zm_ascii
    sys.modules["zaber_motion"] = _zm
    sys.modules["zaber_motion.ascii"] = _zm_ascii

from tvam_code import load_images_and_correct_rotation_axis_wobbling, write_parameters


ENCODER_COUNTS_PER_TURN = 2 ** 22   # ECM-E3M-C2..: 22-bit incremental encoder
MAX_VELOCITY_DEG_S = 1800           # 300 rpm. Raise only if the vial mount is safe for it.
TRIGGER_JITTER_US = 5               # Arduino loop jitter + filter latency, kept as safety
DMD_ROWS, DMD_COLS = 768, 1024


# --------------------------------------------------------------------------
# Arguments
# --------------------------------------------------------------------------
def process_arguments():
    parser = argparse.ArgumentParser(description="TVAM printing with the Delta E3 servo.")

    # same meaning as in tvam_code.py
    parser.add_argument('-v', '--velocity', type=float, default=360.0, help="rotation speed in deg/s, default 360")
    parser.add_argument('-n', '--num_turns', type=int, default=3, help="number of printing turns, default 3")
    parser.add_argument('-d', '--duty_cycle', type=float, default=1.0,
                        help="fraction of each frame the mirrors are on. 1 = no dark gap between frames")
    parser.add_argument('-p', '--path', help="folder of patterns or .npz file (ANGLES x 768 x 1024)")
    parser.add_argument('-a', '--amplitude', type=float, default=0, help="wobble amplitude in DMD pixels")
    parser.add_argument('-ph', '--phase', type=float, default=0, help="wobble phase in degrees")
    parser.add_argument('--reverse_angles', action='store_true')
    parser.add_argument('--flip_vertical', action='store_true')
    parser.add_argument('--flip_horizontal', action='store_true')
    parser.add_argument('--shift_vertical', type=int, default=0)
    parser.add_argument('--mode_horizontal', action='store_true')
    parser.add_argument('-f', '--flat_field', type=str, default="None")
    parser.add_argument('--notes', type=str, default="None")

    # new for the servo setup
    parser.add_argument('-K', '--subframes', type=int, default=1,
                        help="frames per pattern. Default 1")
    parser.add_argument('--port_drive', type=str, default="COM5", help="serial port of the RS-485 adapter (drive CN3)")
    parser.add_argument('--drive_address', type=int, default=0x7F, help="Modbus address of the drive (P3.000), default 0x7F")
    parser.add_argument('--drive_baud', type=int, default=38400, help="RS-485 baud rate (P3.001), default 38400")
    parser.add_argument('--port_arduino', type=str, default="COM3", help="serial port of the trigger Arduino")
    parser.add_argument('--margin', type=float, default=0.05,
                        help="DMD frame is this much shorter than the trigger period (speed ripple), default 0.05")
    parser.add_argument('--accel_ms', type=int, default=1000,
                        help="ramp time 0 -> 3000 rpm (P1.034 / P1.035), default 1000 ms")
    parser.add_argument('--settle', type=float, default=2.0, help="extra wait after reaching speed, default 2 s")
    parser.add_argument('--check_turns', type=int, default=3,
                        help="turns counted before each print to check OA/Z wiring, default 3 (0 = skip)")
    parser.add_argument('--ignore_check', action='store_true', help="print even if the pulse count check fails")
    parser.add_argument('--zpol', type=int, default=0, choices=[0, 1],
                        help="Z polarity at Arduino D2: 0 = OCZ open collector (default), 1 = OZ through AM26C32")
    parser.add_argument('--pulse_us', type=int, default=10, help="trigger pulse width to the DMD, default 10 us")
    parser.add_argument('--reverse_rotation', action='store_true', help="spin the motor the other way")
    parser.add_argument('--alp_version', type=str, default="4.2",
                        help="ALP API version, default 4.2 like tvam_code.py (LED setup uses 4.3)")
    parser.add_argument('--alp_libdir', type=str, default=None,
                        help="folder with the ALP .dll, e.g. '.' for the x64 folder copy (LED setup)")
    parser.add_argument('--emgs', action='store_true',
                        help="an E-stop (normally closed) is wired to DI8 (CN1 pin 30) with 24 V on COM+")

    # modes
    parser.add_argument('--setup_drive', action='store_true',
                        help="one-time: put the drive in Sz speed mode, then power-cycle it")
    parser.add_argument('--check_only', action='store_true',
                        help="spin the motor and count OA pulses per turn, no DMD")
    parser.add_argument('--frames_per_rev', type=int, default=None, help="frames per turn for --check_only")

    args = parser.parse_args()

    if args.setup_drive:
        return args
    assert 0 < args.duty_cycle <= 1.0, "Duty cycle has to be > 0 and <= 1"
    assert 0 < abs(args.velocity) <= MAX_VELOCITY_DEG_S, \
        "Velocity must be between 0 and {} deg/s (MAX_VELOCITY_DEG_S)".format(MAX_VELOCITY_DEG_S)
    assert args.num_turns >= 1, "Do at least one turn"
    assert args.subframes >= 1, "subframes must be >= 1"
    assert 0 < args.margin < 0.5, "margin must be between 0 and 0.5"
    if args.check_only:
        assert args.frames_per_rev, "--check_only needs --frames_per_rev"
    else:
        assert args.path, "give the patterns with -p"
    return args


# --------------------------------------------------------------------------
# Delta ASD-E3-L drive over Modbus RTU (CN3, RS-485)
# --------------------------------------------------------------------------
class DeltaE3:
    """Minimal Modbus access. Parameter Px.yyy lives at address x*0x100 + 2*yyy.
    32-bit values are sent low word first (manual section 9.3)."""

    # P4.007 software DI bits
    DI_SON, DI_SPD0, DI_ARST = 0x0001, 0x0004, 0x0010

    def __init__(self, port, address, baud):
        import minimalmodbus
        import serial
        self.inst = minimalmodbus.Instrument(port, address, mode=minimalmodbus.MODE_RTU)
        self.inst.serial.baudrate = baud
        self.inst.serial.bytesize = 8
        self.inst.serial.parity = serial.PARITY_NONE
        self.inst.serial.stopbits = 2            # P3.002 default: 8N2 RTU
        self.inst.serial.timeout = 0.5
        self.inst.clear_buffers_before_each_transaction = True

    @staticmethod
    def addr(param):
        group, number = param[1:].split(".")
        return int(group) * 0x100 + int(number) * 2

    def read16(self, p):
        return self.inst.read_register(self.addr(p), functioncode=3)

    def write16(self, p, value):
        self.inst.write_register(self.addr(p), value & 0xFFFF, functioncode=6)

    def read32(self, p):
        lo, hi = self.inst.read_registers(self.addr(p), 2, functioncode=3)
        value = (hi << 16) | lo
        return value - (1 << 32) if value & 0x80000000 else value

    def write32(self, p, value):
        value &= 0xFFFFFFFF
        self.inst.write_registers(self.addr(p), [value & 0xFFFF, value >> 16])

    # ---- setup ----
    def setup_speed_mode(self):
        self.write16("P2.030", -5)               # make sure the next write is saved to EEPROM
        self.write16("P4.007", 0)
        self.write16("P1.001", 0x0004)           # Sz: speed mode with internal speed registers
        print("Drive set to Sz speed mode (P1.001 = 0x0004). Power-cycle the drive now.")

    def check_alarm(self):
        alarm = self.read16("P0.001")
        if alarm:
            raise RuntimeError("Drive shows alarm AL{:03X}. Check the drive display / manual chapter 12.".format(alarm))

    def configure(self, frames_per_rev, accel_ms, emgs):
        if self.read16("P1.001") & 0xFF != 0x04:
            raise RuntimeError("Drive is not in Sz speed mode. Run once with --setup_drive, then power-cycle the drive.")
        self.check_alarm()

        self.write16("P2.030", 5)                # everything below is volatile, no EEPROM wear
        self.write16("P4.007", 0)                # servo off
        self.write16("P2.010", 0x0101)           # DI1 = SON (servo on)
        self.write16("P2.011", 0x0000)
        self.write16("P2.012", 0x0114)           # DI3 = SPD0 -> speed command = P1.009
        self.write16("P2.013", 0x0000)
        self.write16("P2.014", 0x0102)           # DI5 = ARST (alarm reset)
        self.write16("P2.015", 0x0000)           # no negative limit switch
        self.write16("P2.016", 0x0000)           # no positive limit switch
        self.write16("P2.017", 0x0021 if emgs else 0x0000)   # DI8 = E-stop, normally closed
        self.write16("P3.006", 0x0015)           # DI1, DI3, DI5 driven from P4.007 (software)

        self.write32("P1.097", 0)
        self.write32("P1.046", frames_per_rev)   # OA pulses per turn (servo must be off)
        self.write16("P1.034", accel_ms)
        self.write16("P1.035", accel_ms)
        self.write16("P0.017", 7)                # P0.009 now reads motor speed in rpm

        if self.read32("P1.046") != frames_per_rev:
            raise RuntimeError("P1.046 did not take the value {}".format(frames_per_rev))

    # ---- motion ----
    def set_speed_rpm(self, rpm):
        """Returns the rpm that was really set (0.1 rpm resolution)."""
        value = int(round(rpm * 10))
        self.write32("P1.009", value)
        return value / 10

    def servo_on(self):
        self.write16("P4.007", self.DI_SON)

    def run(self):
        self.write16("P4.007", self.DI_SON | self.DI_SPD0)

    def stop(self):
        self.write16("P4.007", self.DI_SON)      # speed command 0, ramps down with P1.035

    def servo_off(self):
        self.write16("P4.007", 0)

    def speed_rpm(self):
        return self.read32("P0.009")


# --------------------------------------------------------------------------
# Arduino trigger board
# --------------------------------------------------------------------------
class TriggerBoard:
    def __init__(self, port):
        import serial
        self.ser = serial.Serial(port, 115200, timeout=0.2)
        time.sleep(2.0)                          # the Uno resets when the port opens
        self.ser.reset_input_buffer()
        self.ser.write(b"?\n")
        reply = self._readline(3.0)
        if not reply.startswith("TVAM-SERVO"):
            raise RuntimeError("Trigger Arduino on {} did not answer (got {!r}). "
                               "Is arduino_servo_trigger.ino flashed?".format(port, reply))

    def _readline(self, timeout):
        end = time.time() + timeout
        while time.time() < end:
            line = self.ser.readline().decode(errors="replace").strip()
            if line:
                return line
        return ""

    def configure(self, frames_per_rev, lock_us, pulse_us, zpol):
        self.ser.write("S {} {} {} {}\n".format(frames_per_rev, int(lock_us), int(pulse_us), zpol).encode())
        reply = self._readline(2.0)
        if reply != "OK":
            raise RuntimeError("Trigger Arduino rejected settings: {!r}".format(reply))

    def collect(self, timeout, desc=None):
        """Wait for the RESULT line. Shows a time-based progress bar when desc is given."""
        counts, end, start = [], time.time() + timeout, time.time()
        bar = tqdm.tqdm(total=round(timeout), desc=desc, bar_format='{l_bar}{bar}{r_bar}') if desc else None
        try:
            while time.time() < end:
                line = self.ser.readline().decode(errors="replace").strip()
                if bar:
                    bar.update(min(round(time.time() - start), bar.total) - bar.n)
                if line.startswith("REV "):
                    counts.append(int(line.split()[2]))
                elif line.startswith("RESULT "):
                    _, sent, turns, rejected, spikes, status = line.split()
                    return dict(sent=int(sent), turns=int(turns), rejected=int(rejected),
                                spikes=int(spikes), status=status, counts=counts)
        finally:
            if bar:
                bar.close()
        self.abort()
        raise RuntimeError("Trigger Arduino did not report back in time")

    def count(self, turns, timeout):
        self.ser.write("C {}\n".format(turns).encode())
        return self.collect(timeout)

    def arm(self, frames):
        self.ser.write("A {}\n".format(frames).encode())

    def abort(self):
        self.ser.write(b"x")


def check_counts(result, frames_per_rev):
    """True if every turn delivered exactly frames_per_rev OA edges.
    Z can land within a few us of an OA edge, so one turn may read +-1;
    the running total must still stay within +-1."""
    counts = np.array(result["counts"], dtype=np.int64)
    if len(counts) == 0:
        return False, "no complete turn measured"
    drift = np.cumsum(counts - frames_per_rev)
    ok = (np.all(np.abs(counts - frames_per_rev) <= 1) and np.max(np.abs(drift)) <= 1
          and result["rejected"] == 0 and result["spikes"] == 0)
    text = ("per-turn OA count min {} / max {} (expected {}), running drift {}, "
            "rejected edges {}, short spikes {}").format(
        counts.min(), counts.max(), frames_per_rev, int(np.max(np.abs(drift))),
        result["rejected"], result["spikes"])
    return bool(ok), text


# --------------------------------------------------------------------------
# Patterns -> DMD frames
# --------------------------------------------------------------------------
def bayer_matrix(n):
    m = np.array([[0]])
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return (m + 0.5) / m.size


def binary_frames(images, K, first_frame, n_frames):
    """DMD frames [first_frame, first_frame + n_frames). Pattern a becomes K frames."""
    threshold = np.tile(bayer_matrix(8), (DMD_ROWS // 8, DMD_COLS // 8)).astype(np.float32)
    out = np.empty((n_frames, DMD_ROWS * DMD_COLS // 8), dtype=np.uint8)
    for i in range(n_frames):
        a, k = divmod(first_frame + i, K)
        level = images[a].reshape(DMD_ROWS, DMD_COLS).astype(np.float32) * (K / 255.0)
        out[i] = np.packbits(level > (k + threshold), axis=-1).reshape(-1)
    return out


# --------------------------------------------------------------------------
# DMD
# --------------------------------------------------------------------------
def initialize_DMD(images, args, frames_per_rev, velocity):
    total_frames = frames_per_rev           # the sequence holds one turn, repeated num_turns times
    if args.alp_libdir:
        dmd = ALP4(version=args.alp_version, libDir=args.alp_libdir)
    else:
        dmd = ALP4(version=args.alp_version)
    dmd.Initialize()

    available = dmd.DevInquire(ALP_AVAIL_MEMORY)
    assert total_frames <= available, \
        "{} frames do not fit in DMD memory ({} available). Use fewer patterns or a smaller K.".format(
            total_frames, available)

    dmd.SeqAlloc(nbImg=total_frames, bitDepth=1)
    dmd.SeqControl(ALP_DATA_FORMAT, ALP_DATA_BINARY_TOPDOWN)
    dmd.SeqControl(ALP_BIN_MODE, ALP_BIN_UNINTERRUPTED if args.duty_cycle >= 1 else ALP_BIN_NORMAL)
    dmd.SeqControl(ALP_SEQ_REPEAT, args.num_turns)                 # DMD stops by itself afterwards

    chunk = 256
    print("Uploading {} frames ({} patterns x K={}) to the DMD.".format(
        total_frames, images.shape[0], args.subframes))
    for start in tqdm.tqdm(range(0, total_frames, chunk)):
        n = min(chunk, total_frames - start)
        data = np.ascontiguousarray(binary_frames(images, args.subframes, start, n))
        dmd.SeqPut(imgData=data, PicOffset=start, PicLoad=n)

    rate = velocity / 360 * frames_per_rev
    period_us = 1e6 / rate
    picture_us = int(period_us * (1 - args.margin) - TRIGGER_JITTER_US)
    min_picture_us = dmd.SeqInquire(ALP_MIN_PICTURE_TIME)
    assert picture_us >= min_picture_us, (
        "Trigger rate {:.0f} Hz is too fast: frame time {} us < DMD minimum {} us. "
        "Lower -v, -K or the number of patterns.".format(rate, picture_us, min_picture_us))

    if args.duty_cycle >= 1:
        dmd.SetTiming(pictureTime=picture_us)
    else:
        illumination_us = int(picture_us * args.duty_cycle)
        min_illumination_us = dmd.SeqInquire(ALP_MIN_ILLUMINATE_TIME)
        assert illumination_us >= min_illumination_us, \
            "illumination {} us below DMD minimum {} us, raise the duty cycle".format(
                illumination_us, min_illumination_us)
        dmd.SetTiming(pictureTime=picture_us, illuminationTime=illumination_us)
    illumination_us = dmd.SeqInquire(ALP_ILLUMINATE_TIME)

    dmd.ProjControl(ALP_PROJ_MODE, ALP_SLAVE)
    dmd.DevControl(ALP_TRIGGER_EDGE, ALP_EDGE_RISING)
    print("DMD: {:.0f} frames/s, period {:.1f} us, picture {} us, illumination {} us.\n".format(
        rate, period_us, picture_us, illumination_us))
    return dmd, illumination_us


def free_DMD(dmd):
    for call in (dmd.Halt, dmd.FreeSeq, dmd.Free):
        try:
            call()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Motion helpers
# --------------------------------------------------------------------------
def spin_up(drive, rpm, args):
    drive.servo_on()
    time.sleep(0.5)
    drive.check_alarm()
    drive.run()
    ramp = args.accel_ms / 1000 * abs(rpm) / 3000
    print("Ramping up to {:.1f} rpm ({:.1f} s) and settling {:.1f} s.".format(rpm, ramp, args.settle))
    time.sleep(ramp + args.settle)
    measured = drive.speed_rpm()
    if abs(measured - rpm) > max(1.0, 0.03 * abs(rpm)):
        raise RuntimeError("Motor runs at {} rpm instead of {:.1f} rpm".format(measured, rpm))
    print("Motor speed {} rpm.".format(measured))


def spin_down(drive, args):
    try:
        drive.stop()
        end = time.time() + args.accel_ms / 1000 * 2 + 3
        while time.time() < end and abs(drive.speed_rpm()) > 1:
            time.sleep(0.1)
    finally:
        drive.servo_off()


def self_check(board, frames_per_rev, turns, velocity):
    timeout = (turns + 1) * 360 / abs(velocity) + 6   # up to one extra turn waiting for the first Z
    result = board.count(turns, timeout)
    ok, text = check_counts(result, frames_per_rev)
    print(("Pulse check OK: " if ok else "Pulse check FAILED: ") + text)
    if result["status"] != "OK":
        print("Trigger board status: {} (NOZ = no Z pulse, NOOA = no OA pulses)".format(result["status"]))
        ok = False
    return ok, text


def log(text):
    with open('printing_log.txt', 'a') as f:
        f.write(" " + text)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    print("-------------------- 1/6 arguments ---------------------------")
    args = process_arguments()

    if args.setup_drive:
        DeltaE3(args.port_drive, args.drive_address, args.drive_baud).setup_speed_mode()
        return

    write_parameters(args)
    direction = -1 if args.reverse_rotation else 1

    images = None
    if args.check_only:
        frames_per_rev = args.frames_per_rev
    else:
        print("-------------------- 2/6 patterns ----------------------------")
        images = load_images_and_correct_rotation_axis_wobbling(args)
        frames_per_rev = images.shape[0] * args.subframes

    if ENCODER_COUNTS_PER_TURN % frames_per_rev != 0:
        print("Note: {} frames per turn does not divide 2^22 encoder counts. The drive interpolates, "
              "the pulse check below shows whether every turn still gets exactly {} pulses.".format(
                  frames_per_rev, frames_per_rev))

    print("-------------------- 3/6 drive + trigger board ---------------")
    drive = DeltaE3(args.port_drive, args.drive_address, args.drive_baud)
    drive.configure(frames_per_rev, args.accel_ms, args.emgs)
    rpm = drive.set_speed_rpm(direction * abs(args.velocity) / 6)
    velocity = abs(rpm) * 6                       # what the drive really runs at, deg/s
    period_us = 1e6 / (velocity / 360 * frames_per_rev)

    board = TriggerBoard(args.port_arduino)
    board.configure(frames_per_rev, lock_us=min(period_us / 2, 30000),
                    pulse_us=min(args.pulse_us, period_us / 4), zpol=args.zpol)
    if not args.emgs:
        print("WARNING: no hardware E-stop configured (--emgs). Ctrl+C stops the motor in software only.")

    dmd, illumination_us = None, None
    try:
        if not args.check_only:
            print("-------------------- 4/6 DMD ---------------------------------")
            dmd, illumination_us = initialize_DMD(images, args, frames_per_rev, velocity)

        print("-------------------- 5/6 ramp up + pulse check ---------------")
        spin_up(drive, rpm, args)
        if args.check_turns > 0 or args.check_only:
            ok, text = self_check(board, frames_per_rev, max(args.check_turns, 1), velocity)
            log("PulseCheck: " + text)
            if args.check_only:
                return
            if not ok and not args.ignore_check:
                raise RuntimeError("Pulse check failed, not printing. Check OA/Z wiring and noise "
                                   "(or use --ignore_check).")

        print("-------------------- 6/6 printing ----------------------------")
        total = frames_per_rev * args.num_turns
        dmd.Run(loop=False)                       # waits for triggers
        board.arm(total)                          # starts on the next Z = angle 0
        print_time = 360 / velocity * args.num_turns
        result = board.collect(print_time + 360 / velocity + 5, desc="Printinggggg")

        ok, text = check_counts(result, frames_per_rev) if result["counts"] else (True, "")
        print("Triggers sent {} of {}. {}".format(result["sent"], total, text))
        log("Sent:{}/{} Status:{} {}".format(result["sent"], total, result["status"], text))
        if result["sent"] != total or result["status"] != "OK":
            print("WARNING: print incomplete ({}).".format(result["status"]))

        time.sleep(0.1)
        try:
            dmd_done = dmd.ProjInquire(ALP_PROJ_STATE) == ALP_PROJ_IDLE
        except Exception:
            dmd_done = True                       # cannot tell, don't raise a false alarm
        if not dmd_done:
            print("WARNING: DMD did not finish its frames -> it missed triggers. Increase --margin or lower -v.")
            log("DMD missed triggers")
        print("Total printing time {:.1f} s.".format(print_time))

    except KeyboardInterrupt:
        print("Keyboard interrupt, stopping.")
        board.abort()
    finally:
        if dmd is not None:
            free_DMD(dmd)
        spin_down(drive, args)

    if not args.check_only:
        result_text = input("Please add your results ")
        log("IlluminationTime: {}us Final results: {}".format(illumination_us, result_text))


if __name__ == "__main__":
    main()
