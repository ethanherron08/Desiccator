# gui.py

import os

from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QComboBox
)

from serial.tools import list_ports

from serial_reader import SerialReader


class ScaleLoggerGUI(QWidget):

    def __init__(self):
        super().__init__()

        self.reader = None
        self.sample_count = 0

        self.setWindowTitle(
            "Desiccator v1.0.1 for Ohaus Adventurer"
        )

        self.resize(700, 500)

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout()

        # -------------------------
        # PORT SELECTION
        # -------------------------

        port_layout = QHBoxLayout()

        self.port_combo = QComboBox()

        self.refresh_button = QPushButton(
            "Refresh Ports"
        )

        self.test_button = QPushButton(
            "Test Port (For very short auto print time)"
        )

        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.refresh_button)
        port_layout.addWidget(self.test_button)

        layout.addLayout(port_layout)

        # -------------------------
        # STATUS
        # -------------------------

        self.status_label = QLabel(
            "Status: Disconnected"
        )

        self.weight_label = QLabel(
            "Last Weight: ---"
        )

        self.time_label = QLabel(
            "Last Reading: ---"
        )

        self.count_label = QLabel(
            "Samples Logged: 0"
        )

        layout.addWidget(self.status_label)
        layout.addWidget(self.weight_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.count_label)

        # -------------------------
        # FILE SELECTION
        # -------------------------

        self.file_button = QPushButton(
            "Select CSV File"
        )

        self.file_label = QLabel(
            "No file selected"
        )

        layout.addWidget(self.file_button)
        layout.addWidget(self.file_label)

        # -------------------------
        # START/STOP CONTROLS
        # -------------------------

        control_layout = QHBoxLayout()

        self.start_button = QPushButton(
            "Start Logging"
        )

        self.stop_button = QPushButton(
            "Stop Logging"
        )

        self.stop_button.setEnabled(False)

        control_layout.addWidget(
            self.start_button
        )

        control_layout.addWidget(
            self.stop_button
        )

        layout.addLayout(control_layout)

        # -------------------------
        # LOG WINDOW
        # -------------------------

        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)

        layout.addWidget(self.log_window)

        self.setLayout(layout)

        # -------------------------
        # INITIALIZE
        # -------------------------

        self.refresh_ports()

        # -------------------------
        # SIGNALS
        # -------------------------

        self.refresh_button.clicked.connect(
            self.refresh_ports
        )

        self.test_button.clicked.connect(
            self.test_port
        )

        self.file_button.clicked.connect(
            self.select_file
        )

        self.start_button.clicked.connect(
            self.start_logging
        )

        self.stop_button.clicked.connect(
            self.stop_logging
        )

    def refresh_ports(self):

        self.port_combo.clear()

        ports = list_ports.comports()

        for port in ports:

            manufacturer = (
                port.manufacturer
                if port.manufacturer
                else "Unknown"
            )

            display_text = (
                f"{manufacturer} - "
                f"{port.description} "
                f"({port.device})"
            )

            self.port_combo.addItem(
                display_text,
                port.device
            )

    def test_port(self):

        from serial import Serial

        try:

            port = self.port_combo.currentData()

            if not port:

                QMessageBox.warning(
                    self,
                    "Warning",
                    "No COM port selected."
                )
                return

            ser = Serial(
                port,
                9600,
                timeout=3
            )

            ser.close()

            QMessageBox.information(
                self,
                "Success",
                f"{port} opened successfully."
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

    def select_file(self):

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select CSV File",
            "scale_log.csv",
            "CSV Files (*.csv)"
        )

        if filename:

            self.file_label.setText(
                filename
            )

            if not os.path.exists(filename):

                with open(
                    filename,
                    "w",
                    newline=""
                ) as f:

                    f.write(
                        "timestamp,weight,units\n"
                    )

    def start_logging(self):

        if self.file_label.text() == "No file selected":

            QMessageBox.warning(
                self,
                "Warning",
                "Select output file first."
            )

            return

        port = self.port_combo.currentData()

        if not port:

            QMessageBox.warning(
                self,
                "Warning",
                "Select a COM port."
            )

            return

        csv_file = self.file_label.text()

        self.reader = SerialReader(
            port,
            9600,
            csv_file
        )

        self.reader.new_reading.connect(
            self.update_reading
        )

        self.reader.status_update.connect(
            self.update_status
        )

        self.reader.log_message.connect(
            self.append_log
        )

        self.reader.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_logging(self):

        if self.reader:

            self.reader.stop()
            self.reader.wait()

        self.status_label.setText(
            "Status: Stopped"
        )

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_reading(
        self,
        weight,
        units,
        timestamp
    ):

        self.sample_count += 1

        self.weight_label.setText(
            f"Last Weight: {weight} {units}"
        )

        self.time_label.setText(
            f"Last Reading: {timestamp}"
        )

        self.count_