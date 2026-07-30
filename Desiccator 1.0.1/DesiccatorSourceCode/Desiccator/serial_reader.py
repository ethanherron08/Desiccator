# serial_reader.py
"""
Serial acquisition thread for the Desiccator logger.

Key differences from the previous version:
  * Byte-level buffering instead of ser.readline(), so CR-only, LF-only and
    CRLF terminators all work.
  * Explicit framing parameters (bytesize / parity / stopbits / handshake)
    instead of relying on pyserial defaults.
  * DTR and RTS are explicitly asserted -- many balances will not transmit
    until they see these lines high.
  * Optional poll mode: sends a print command on an interval, so you are not
    dependent on the scale's auto-print being configured correctly.
  * Every state transition emits a status string, and every raw byte received
    is surfaced to the GUI log so a silent port is distinguishable from a
    port that is talking but not parsing.
  * finally: block guarantees the port is closed, so a crashed run does not
    leave COMx locked against the next attempt.
"""

import csv
import os
import re
import time
import traceback
from datetime import datetime

import serial
from PySide6.QtCore import QThread, Signal


# Longest units first so 'kg' is not shadowed by 'g'.
WEIGHT_WITH_UNIT = re.compile(
    r'([+-]?\d+(?:\.\d+)?)\s*(mg|kg|lb|oz|ct|gn|g)\b',
    re.IGNORECASE,
)

# Fallback for balances that print a bare number with no unit.
BARE_NUMBER = re.compile(r'^[+-]?\d+(?:\.\d+)?$')


class SerialReader(QThread):

    new_reading = Signal(float, str, str)   # weight, units, timestamp
    status_update = Signal(str)
    log_message = Signal(str)

    def __init__(
        self,
        port,
        baudrate,
        csv_file,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        handshake="none",          # "none" | "xonxoff" | "rtscts"
        default_units="g",
        poll_enabled=False,
        poll_command="P\r\n",
        poll_interval=10.0,
    ):
        super().__init__()

        self.port = port
        self.baudrate = int(baudrate)
        self.csv_file = csv_file

        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.handshake = handshake
        self.default_units = default_units

        self.poll_enabled = poll_enabled
        self.poll_command = poll_command
        self.poll_interval = float(poll_interval)

        self.running = False

    def stop(self):
        self.running = False

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _ensure_header(self):
        """Create the CSV with a header row if it is missing or empty."""
        need_header = (
            not os.path.exists(self.csv_file)
            or os.path.getsize(self.csv_file) == 0
        )
        if need_header:
            with open(self.csv_file, "w", newline="") as f:
                csv.writer(f).writerow(
                    ["timestamp", "weight", "units", "raw"]
                )

    def _parse(self, text):
        """Return (weight, units) or None."""
        cleaned = text.replace("\x02", "").replace("\x03", "").strip()
        if not cleaned:
            return None

        m = WEIGHT_WITH_UNIT.search(cleaned)
        if m:
            return float(m.group(1)), m.group(2).lower()

        if BARE_NUMBER.match(cleaned):
            return float(cleaned), self.default_units

        return None

    # ------------------------------------------------------------------
    # thread body
    # ------------------------------------------------------------------

    def run(self):

        ser = None
        self.running = True

        try:
            self.status_update.emit(f"Opening {self.port} ...")

            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=0.25,
                xonxoff=(self.handshake == "xonxoff"),
                rtscts=(self.handshake == "rtscts"),
                dsrdtr=False,
            )

            # Assert control lines. Some balances gate their output on these.
            try:
                ser.dtr = True
                ser.rts = True
            except Exception:
                pass

            ser.reset_input_buffer()
            ser.reset_output_buffer()

            self.status_update.emit(f"Connected - {self.port}")
            self.log_message.emit(
                f"[open] {self.port} @ {self.baudrate} "
                f"{ser.bytesize}{ser.parity}{ser.stopbits} "
                f"handshake={self.handshake}"
            )
            self.log_message.emit(
                f"[lines] CTS={ser.cts} DSR={ser.dsr} CD={ser.cd} RI={ser.ri}"
            )

            self._ensure_header()

            buffer = bytearray()
            last_poll = 0.0
            last_heartbeat = time.monotonic()
            bytes_total = 0

            with open(self.csv_file, "a", newline="") as f:

                writer = csv.writer(f)

                while self.running:

                    # -- optional polling ------------------------------
                    now = time.monotonic()
                    if self.poll_enabled and (now - last_poll) >= self.poll_interval:
                        try:
                            ser.write(self.poll_command.encode("ascii"))
                            ser.flush()
                            self.log_message.emit(
                                f"[poll] sent {self.poll_command!r}"
                            )
                        except Exception as e:
                            self.log_message.emit(f"[poll error] {e}")
                        last_poll = now

                    # -- read whatever is available --------------------
                    waiting = ser.in_waiting
                    chunk = ser.read(waiting if waiting else 1)

                    if chunk:
                        bytes_total += len(chunk)
                        buffer.extend(chunk)
                        last_heartbeat = time.monotonic()
                    else:
                        # Nothing arrived this cycle. Emit a heartbeat every
                        # 30 s so a dead port is obvious in the log window.
                        if time.monotonic() - last_heartbeat > 30:
                            self.log_message.emit(
                                f"[idle] no data for 30 s "
                                f"(total bytes {bytes_total})"
                            )
                            last_heartbeat = time.monotonic()
                        continue

                    # -- split on CR, LF or CRLF -----------------------
                    buffer = buffer.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

                    while b"\n" in buffer:
                        line, _, rest = buffer.partition(b"\n")
                        buffer = bytearray(rest)

                        text = line.decode("utf-8", errors="replace").strip()
                        if not text:
                            continue

                        self.log_message.emit(f"RX: {text}")

                        parsed = self._parse(text)

                        if parsed is None:
                            self.log_message.emit(
                                f"   (no weight parsed) hex={line.hex(' ')}"
                            )
                            continue

                        weight, units = parsed
                        timestamp = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        writer.writerow([timestamp, weight, units, text])
                        f.flush()
                        os.fsync(f.fileno())

                        self.new_reading.emit(weight, units, timestamp)

        except serial.SerialException as e:
            self.status_update.emit(f"Error: {e}")
            self.log_message.emit(
                "[SerialException] " + traceback.format_exc()
            )

        except Exception as e:
            self.status_update.emit(f"Error: {e}")
            self.log_message.emit("[Exception] " + traceback.format_exc())

        finally:
            if ser is not None:
                try:
                    ser.close()
                    self.log_message.emit(f"[closed] {self.port}")
                except Exception:
                    pass
            self.running = False
            self.status_update.emit("Disconnected")
