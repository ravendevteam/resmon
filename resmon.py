import sys
import os
import psutil
import platform
import subprocess
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QAction, QWidget,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, QMessageBox, QMenu,
    QTableWidget, QHeaderView, QSplitter, QTableWidgetItem, QLabel, QTextBrowser, QTabWidget, QProgressBar
)

prevDrive = None

class ProcessFetcher(QThread):
    update_processes = pyqtSignal(list)
    update_stats = pyqtSignal(float, float, str)
    update_drives = pyqtSignal(list)

    def run(self):
        while True:
            processes_info = []
            for proc in psutil.process_iter(['pid', 'name', 'num_threads', 'username', 'memory_info', 'cpu_percent']):
                if proc.info['name'] == "System Idle Process":
                    continue
                processes_info.append([
                    proc.info['pid'],
                    proc.info['name'],
                    proc.info['num_threads'],
                    proc.info['username'],
                    proc.info['memory_info'].rss / (1024 * 1024),
                    round(proc.info['cpu_percent'], 1)
                ])
            self.update_processes.emit(processes_info)
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            boot_drive = psutil.disk_partitions()[0].device
            disk_info = psutil.disk_usage(boot_drive)
            total_disk = disk_info.total / (1024**3)
            used_disk = disk_info.used / (1024**3)
            used_percentage = used_disk / total_disk * 100
            disk_display = f"{used_percentage:.1f}%"
            self.update_stats.emit(cpu_usage, memory_info.percent, disk_display)
            self.update_drives.emit(psutil.disk_partitions())

class SystemInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Information")
        self.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout(self)
        self.info_browser = QTextBrowser(self)
        layout.addWidget(self.info_browser)
        self.display_system_info()

    def display_system_info(self):
        try:
            process = subprocess.Popen("systeminfo", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                self.info_browser.setPlainText(stdout)
            else:
                self.info_browser.setPlainText(f"Error running systeminfo command: {stderr}")
        except Exception as e:
            self.info_browser.setPlainText(f"An error occurred: {str(e)}")

class Resmon(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resmon")
        self.setGeometry(100, 100, 770, 700)
        self.always_on_top = False
        self.selected_pid = None
        self.init_ui()
        self.fetcher = ProcessFetcher()
        self.fetcher.update_processes.connect(self.update_process_table)
        self.fetcher.update_drives.connect(self.update_drives)
        self.fetcher.update_stats.connect(self.update_stats)
        self.fetcher.start()

    def init_ui(self):
        self.apply_stylesheet()
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_widget.setLayout(main_layout)
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        start_process_action = QAction("Start a Process", self)
        start_process_action.triggered.connect(self.start_process)
        file_menu.addAction(start_process_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        options_menu = menu_bar.addMenu("Options")
        always_on_top_action = QAction("Always on Top", self, checkable=True)
        always_on_top_action.triggered.connect(self.toggle_always_on_top)
        options_menu.addAction(always_on_top_action)
        view_system_info_action = QAction("View System Information", self)
        view_system_info_action.triggered.connect(self.view_system_info)
        options_menu.addAction(view_system_info_action)
        self.process_table = QTableWidget(self)
        self.process_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.process_table.setSelectionMode(QTableWidget.SingleSelection)
        self.process_table.setColumnCount(6)
        self.process_table.setHorizontalHeaderLabels(["Process ID", "Program", "Threads", "User", "Memory", "CPU"])
        self.process_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.process_table.customContextMenuRequested.connect(self.show_process_context_menu)
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        top_widget = QWidget(self)
        top_layout = QVBoxLayout(top_widget)
        top_widget.setLayout(top_layout)
        stats_layout = QHBoxLayout()
        top_layout.addLayout(stats_layout)

        def create_stat_column(title):
            column_widget = QWidget()
            column_layout = QVBoxLayout(column_widget)
            column_widget.setLayout(column_layout)
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-size: 14px;")
            column_layout.addWidget(title_label)
            value_label = QLabel("0%")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("font-size: 28px; font-weight: bold; color: black;")
            column_layout.addWidget(value_label)
            column_layout.setSpacing(0)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setAlignment(Qt.AlignVCenter)
            return column_widget, value_label

        self.cpu_column, self.cpu_label = create_stat_column("CPU")
        self.memory_column, self.memory_label = create_stat_column("Memory")
        self.disk_column, self.disk_label = create_stat_column(f"Disk ({psutil.disk_partitions()[0].device})")
        stats_layout.addWidget(self.cpu_column)
        stats_layout.addWidget(self.memory_column)
        stats_layout.addWidget(self.disk_column)
        splitter.addWidget(top_widget)
        bottom_widget = QWidget(self)
        bottom_layout = QVBoxLayout(bottom_widget)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.process_table, "Processes")
        self.disk_tab = QWidget()
        self.disk_tab_layout = QVBoxLayout(self.disk_tab)
        self.disk_tab_layout.setAlignment(Qt.AlignTop)
        self.disk_tab.setLayout(self.disk_tab_layout)
        self.tabs.addTab(self.disk_tab, "Drives")
        bottom_layout.addWidget(self.tabs)
        splitter.addWidget(bottom_widget)
        self.process_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        splitter.setSizes([int(self.height() * 0.10), int(self.height() * 0.90)])

    def apply_stylesheet(self):
        stylesheet_path = self.get_default_stylesheet_path()
        try:
            with open(stylesheet_path, 'r') as file:
                stylesheet = file.read()
                self.setStyleSheet(stylesheet)
        except Exception as e:
            QMessageBox.warning(self, "Style Error", f"Failed to apply stylesheet: {e}")

    def get_default_stylesheet_path(self):
        if hasattr(sys, 'frozen'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(__file__)
        return os.path.join(base_path, 'style.css')

    def update_stats(self, cpu_usage, memory_usage, disk_usage):
        self.cpu_label.setText(f"{cpu_usage:.1f}%")
        self.memory_label.setText(f"{memory_usage:.1f}%")
        self.disk_label.setText(disk_usage)

    def update_process_table(self, process_data):
        self.process_table.setRowCount(0)
        sorted_process_data = sorted(process_data, key=lambda x: x[1].lower())
        row_to_select = None
        for index, process in enumerate(sorted_process_data):
            process_id = process[0]
            program_name = process[1]
            threads = process[2]
            user = process[3]
            memory = process[4]
            cpu = process[5]
            if not program_name:
                continue
            row_position = self.process_table.rowCount()
            self.process_table.insertRow(row_position)
            self.process_table.setItem(row_position, 0, QTableWidgetItem(str(process_id)))
            self.process_table.setItem(row_position, 1, QTableWidgetItem(program_name))
            self.process_table.setItem(row_position, 2, QTableWidgetItem(str(threads)))
            self.process_table.setItem(row_position, 3, QTableWidgetItem(user))
            self.process_table.setItem(row_position, 4, QTableWidgetItem(f"{memory:.2f} MB"))
            self.process_table.setItem(row_position, 5, QTableWidgetItem(f"{cpu:.1f}%"))
            if self.selected_pid and self.selected_pid == process_id:
                row_to_select = row_position
        if row_to_select is not None:
            self.process_table.selectRow(row_to_select)

    def update_drives(self, drive_data):
        global prevDrive
        if drive_data == prevDrive:
            return
        prevDrive = drive_data
        disks = drive_data
        for i in reversed(range(self.disk_tab_layout.count())):
            self.disk_tab_layout.itemAt(i).widget().setParent(None)
        for disk in disks:
            drive_path = disk.device
            try:
                disk_info = psutil.disk_usage(drive_path)
            except PermissionError:
                continue
            except OSError:
                continue
            disk_container = QVBoxLayout()
            disk_container.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            disk_info = psutil.disk_usage(disk[1])
            total_disk = disk_info.total
            used_disk = disk_info.used
            used_percentage = used_disk / total_disk * 100
            used_percentage_100k = used_disk / total_disk * 100000

            def format_size(size):
                for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']:
                    if size < 1024:
                        return f"{size:.2f} {unit}"
                    size /= 1024
                return f"{size:.2f} YB"

            total_disk_display = format_size(total_disk)
            used_disk_display = format_size(used_disk)
            disk_display = f"{used_disk_display}/{total_disk_display} ({used_percentage:.1f}%)"
            disk_label = QLabel(f"{disk.device} ({disk.mountpoint})")
            disk_label.setFont(QFont("Arial", 14, QFont.Bold))
            disk_container.addWidget(disk_label)
            filled_disk = QProgressBar()
            filled_disk.setRange(0, 100000)
            filled_disk.setValue(round(used_percentage_100k))
            if used_percentage > 90:
                filled_disk.setStyleSheet("QProgressBar::chunk { background-color: red; }")
            filled_disk.setTextVisible(False)
            disk_container.addWidget(filled_disk)
            disk_usage_label = QLabel(disk_display)
            disk_usage_label.setFont(QFont("Arial", 12))
            disk_container.addWidget(disk_usage_label)
            disk_widget = QWidget()
            disk_widget.setLayout(disk_container)
            self.disk_tab_layout.addWidget(disk_widget)

    def start_process(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Start a Process")
        layout = QFormLayout(dialog)
        process_input = QLineEdit()
        layout.addRow("Run:", process_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.run_process(dialog, process_input.text()))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec_()

    def run_process(self, dialog, command):
        if command:
            try:
                os.startfile(command)
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to start process: {e}")

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        flags = self.windowFlags()
        if self.always_on_top:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    def view_system_info(self):
        dialog = SystemInfoDialog(self)
        dialog.exec_()

    def show_process_context_menu(self, position):
        selected_rows = self.process_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        self.selected_pids = [
            int(self.process_table.item(row.row(), 0).text()) for row in selected_rows
        ]
        menu = QMenu(self)
        terminate_action = QAction("Force Terminate", self)
        terminate_action.triggered.connect(self.force_terminate_selected_processes)
        menu.addAction(terminate_action)
        menu.exec_(self.process_table.viewport().mapToGlobal(position))

    def force_terminate_selected_processes(self):
        for pid in self.selected_pids:
            try:
                process = psutil.Process(pid)
                process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def start_process(self):
        dialog = StartProcessDialog(self)
        if dialog.exec_():
            self.fetcher.start()

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint if self.always_on_top else Qt.Window
        )
        self.show()

    def view_system_info(self):
        dialog = SystemInfoDialog(self)
        dialog.exec_()

class StartProcessDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start a Process")
        layout = QFormLayout(self)
        self.process_name_edit = QLineEdit(self)
        layout.addRow("Process Name:", self.process_name_edit)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def accept(self):
        process_name = self.process_name_edit.text()
        if process_name:
            subprocess.Popen(process_name)
        super().accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Resmon()
    window.show()
    sys.exit(app.exec_())
