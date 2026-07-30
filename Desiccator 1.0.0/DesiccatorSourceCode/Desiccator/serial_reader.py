# serial_reader.py

import serial
import re
import csv
from datetime import datetime

from PySide6.QtCore import QThread, Signal

weight_pattern = re.compile(
    r'([+-]?\d+(?:\.\d+)?)\s*(mg|g|kg|oz|lb)',
    re.IGNORECASE
)


class SerialReader(QThread):

    new_reading = Signal(float, str, str)
    status_update = Signal(str)
    log_message = Signal(str)

    def __init__(self, port, baudrate, csv_file):
        super().__init__()

        self.port = port
        self.baudrate = baudrate
        self.csv_file = csv_file

        self.running = False

    def stop(self):
        self.running = False

    def run(self):

        try:
            ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=1
            )

            self.status_update.emit("Connected")
            self.running = True

            with open(self.csv_file, "a", newline="") as f:

                writer = csv.writer(f)

                while self.running:

                    raw = ser.readline()

                    if not raw:
                        continue

                    text = raw.decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()

                    self.log_message.emit(text)

                    match = weight_pattern.search(text)

                    if match:

                        weight = float(match.group(1))
                        units = match.group(2)

                        timestamp = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        writer.writerow(
                            [timestamp, weight, units]
                        )

                        f.flush()

                        self.new_reading.emit(
                            weight,
                            units,
                            timestamp
                        )

            ser.close()

        except Exception as e:

            self.status_update.emit(
                f"Error: {str(e)}"
            )