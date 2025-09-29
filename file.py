import sys
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox, QTabWidget, QGroupBox, QCheckBox,
    QScrollArea, QFormLayout, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont


# ----------------- CORE CLASSES -----------------

class FileCategory:
    def __init__(self, name: str, extensions: List[str], folder_name: str):
        self.name = name
        self.extensions = [ext.lower() for ext in extensions]
        self.folder_name = folder_name
        self.file_count = 0
        self.enabled = True

    def matches_extension(self, extension: str) -> bool:
        return extension.lower() in self.extensions

    def increment_count(self):
        self.file_count += 1

    def reset_count(self):
        self.file_count = 0


class FileInfo:
    def __init__(self, file_path: Path):
        self.path = file_path
        self.name = file_path.name
        self.extension = file_path.suffix.lower()
        self.size = file_path.stat().st_size if file_path.exists() else 0
        self.modified_time = datetime.fromtimestamp(file_path.stat().st_mtime) if file_path.exists() else None


# ----------------- WORKER THREAD -----------------

class FileOrganizerWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    log_updated = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, source_dir, dest_dir, categories, dry_run=False):
        super().__init__()
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir) if dest_dir else self.source_dir / "Organized"
        self.categories = categories
        self.dry_run = dry_run
        self.should_stop = False

    def stop(self):
        self.should_stop = True

    def run(self):
        try:
            self.organize_files()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def organize_files(self):
        self.log_updated.emit(f"Starting {'dry run' if self.dry_run else 'organization'}")
        self.log_updated.emit(f"Source: {self.source_dir}")
        self.log_updated.emit(f"Destination: {self.dest_dir}")

        files = []
        self.status_updated.emit("Scanning files...")

        try:
            for file_path in self.source_dir.rglob("*"):
                if self.should_stop:
                    return
                if file_path.is_file():
                    files.append(FileInfo(file_path))
        except Exception as e:
            self.error_occurred.emit(f"Error scanning files: {e}")
            return

        if not files:
            self.log_updated.emit("No files found to organize")
            self.finished.emit({'total_files': 0, 'organized': 0, 'uncategorized': 0, 'categories': {}})
            return

        self.log_updated.emit(f"Found {len(files)} files")

        if not self.dry_run:
            self.dest_dir.mkdir(parents=True, exist_ok=True)

        for category in self.categories:
            if category.enabled:
                category.reset_count()

        organized_count = 0
        uncategorized_files = []

        for i, file_info in enumerate(files):
            if self.should_stop:
                return

            progress = int((i / len(files)) * 100)
            self.progress_updated.emit(progress)
            self.status_updated.emit(f"Processing: {file_info.name}")

            if self.dest_dir in file_info.path.parents:
                continue

            category = self.get_category_for_extension(file_info.extension)

            if category and category.enabled:
                if self.dry_run:
                    category.increment_count()
                    organized_count += 1
                    self.log_updated.emit(f"[DRY] Would move {file_info.name} → {category.folder_name}")
                else:
                    if self.move_file(file_info, category):
                        organized_count += 1
            else:
                uncategorized_files.append(file_info)

        if uncategorized_files and not self.dry_run:
            self.handle_uncategorized_files(uncategorized_files)

        self.progress_updated.emit(100)
        self.status_updated.emit("Complete!")

        summary = {
            'total_files': len(files),
            'organized': organized_count,
            'uncategorized': len(uncategorized_files),
            'categories': {cat.name: cat.file_count for cat in self.categories if cat.file_count > 0}
        }

        self.log_updated.emit(f"Organization complete. Processed {organized_count} files.")
        self.finished.emit(summary)

    def get_category_for_extension(self, extension: str) -> Optional[FileCategory]:
        for category in self.categories:
            if category.enabled and category.matches_extension(extension):
                return category
        return None

    def move_file(self, file_info: FileInfo, category: FileCategory) -> bool:
        try:
            category_path = self.dest_dir / category.folder_name
            category_path.mkdir(parents=True, exist_ok=True)

            destination = category_path / file_info.name
            counter = 1
            base_name = file_info.path.stem
            extension = file_info.path.suffix

            while destination.exists():
                new_name = f"{base_name}_{counter}{extension}"
                destination = category_path / new_name
                counter += 1

            shutil.move(str(file_info.path), str(destination))
            category.increment_count()
            self.log_updated.emit(f"Moved {file_info.name} → {category.folder_name}")
            return True

        except Exception as e:
            self.log_updated.emit(f"Error moving {file_info.name}: {e}")
            return False

    def handle_uncategorized_files(self, uncategorized_files: List[FileInfo]):
        if not uncategorized_files:
            return

        uncategorized_path = self.dest_dir / "Uncategorized"
        uncategorized_path.mkdir(parents=True, exist_ok=True)

        for file_info in uncategorized_files:
            try:
                destination = uncategorized_path / file_info.name
                counter = 1
                base_name = file_info.path.stem
                extension = file_info.path.suffix

                while destination.exists():
                    new_name = f"{base_name}_{counter}{extension}"
                    destination = uncategorized_path / new_name
                    counter += 1

                shutil.move(str(file_info.path), str(destination))
                self.log_updated.emit(f"Moved {file_info.name} → Uncategorized")
            except Exception as e:
                self.log_updated.emit(f"Error moving uncategorized file {file_info.name}: {e}")


# ----------------- CATEGORY WIDGET -----------------

class CategoryWidget(QWidget):
    def __init__(self, category: FileCategory, parent=None):
        super().__init__(parent)
        self.category = category
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        self.enabled_cb = QCheckBox()
        self.enabled_cb.setChecked(self.category.enabled)
        self.enabled_cb.toggled.connect(self.on_enabled_changed)
        layout.addWidget(self.enabled_cb)

        name_label = QLabel(self.category.name)
        name_label.setMinimumWidth(130)
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(name_label)

        ext_label = QLabel(", ".join(self.category.extensions))
        ext_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(ext_label, 1)

        folder_label = QLabel(f"→ {self.category.folder_name}")
        folder_label.setStyleSheet("color: #3498db; font-weight: bold;")
        folder_label.setMinimumWidth(120)
        layout.addWidget(folder_label)

        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.count_label.setMinimumWidth(40)
        layout.addWidget(self.count_label)

        # Set initial background
        self.setAutoFillBackground(True)
        self.on_enabled_changed(self.category.enabled)

    def on_enabled_changed(self, checked):
        self.category.enabled = checked
        if checked:
            self.setStyleSheet("CategoryWidget { background-color: white; border-radius: 5px; }")
        else:
            self.setStyleSheet("CategoryWidget { background-color: #f0f0f0; border-radius: 5px; }")

    def update_count(self):
        self.count_label.setText(str(self.category.file_count))


# ----------------- MAIN GUI -----------------

class FileOrganizerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.categories = self.init_default_categories()
        self.worker: Optional[FileOrganizerWorker] = None
        self.category_widgets: List[CategoryWidget] = []
        self.setup_ui()
        self.setup_style()

    def init_default_categories(self):
        return [
            FileCategory("Documents", [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"], "Documents"),
            FileCategory("Images", [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".tiff"], "Images"),
            FileCategory("Videos", [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"], "Videos"),
            FileCategory("Audio", [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"], "Audio"),
            FileCategory("Archives", [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"], "Archives"),
            FileCategory("Code", [".py", ".js", ".html", ".css", ".cpp", ".java", ".php"], "Code"),
            FileCategory("Spreadsheets", [".xlsx", ".xls", ".csv", ".ods"], "Spreadsheets"),
            FileCategory("Presentations", [".ppt", ".pptx", ".odp"], "Presentations"),
            FileCategory("Executables", [".exe", ".msi", ".deb", ".dmg", ".app"], "Executables"),
        ]

    def setup_ui(self):
        self.setWindowTitle("File Organizer - Professional Edition")
        self.setGeometry(80, 80, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Title
        title_label = QLabel("📂 File Organizer")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Tabs
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.main_tab = self.create_main_tab()
        self.tab_widget.addTab(self.main_tab, "Organize Files")

        self.categories_tab = self.create_categories_tab()
        self.tab_widget.addTab(self.categories_tab, "Manage Categories")

        self.logs_tab = self.create_logs_tab()
        self.tab_widget.addTab(self.logs_tab, "Logs & Details")

        self.statusBar().showMessage("Ready")

    def create_main_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Directory selection
        path_group = QGroupBox("Directory Selection")
        path_layout = QFormLayout(path_group)

        source_layout = QHBoxLayout()
        self.source_path = QLineEdit()
        self.source_path.setPlaceholderText("Select source directory...")
        source_btn = QPushButton("Browse")
        source_btn.clicked.connect(self.select_source_directory)
        source_layout.addWidget(self.source_path, 1)
        source_layout.addWidget(source_btn)
        path_layout.addRow("Source Directory:", source_layout)

        dest_layout = QHBoxLayout()
        self.dest_path = QLineEdit()
        self.dest_path.setPlaceholderText("Leave empty to create 'Organized' in source")
        dest_btn = QPushButton("Browse")
        dest_btn.clicked.connect(self.select_dest_directory)
        dest_layout.addWidget(self.dest_path, 1)
        dest_layout.addWidget(dest_btn)
        path_layout.addRow("Destination Directory:", dest_layout)

        layout.addWidget(path_group)

        # Control buttons
        control_layout = QHBoxLayout()

        self.dry_run_btn = QPushButton("Preview (Dry Run)")
        self.dry_run_btn.setObjectName("DryRun")
        self.dry_run_btn.clicked.connect(self.start_dry_run)

        self.organize_btn = QPushButton("Organize Files")
        self.organize_btn.setObjectName("Organize")
        self.organize_btn.clicked.connect(self.start_organization)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("Stop")
        self.stop_btn.clicked.connect(self.stop_organization)
        self.stop_btn.setEnabled(False)

        control_layout.addStretch()
        control_layout.addWidget(self.dry_run_btn)
        control_layout.addWidget(self.organize_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Progress and Results
        bottom_layout = QHBoxLayout()

        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready to organize files")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)
        bottom_layout.addWidget(progress_group, 2)

        results_group = QGroupBox("Results Summary")
        results_layout = QVBoxLayout(results_group)
        self.results_label = QLabel("No organization performed yet")
        self.results_label.setWordWrap(True)
        self.results_label.setStyleSheet("color: #2c3e50; font-size: 13px;")
        results_layout.addWidget(self.results_label)
        bottom_layout.addWidget(results_group, 3)

        layout.addLayout(bottom_layout)

        return widget

    def create_categories_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header_layout = QHBoxLayout()
        title = QLabel("File Categories")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        add_btn = QPushButton("Add Custom Category")
        add_btn.setObjectName("AddCategory")
        add_btn.clicked.connect(self.add_custom_category)
        header_layout.addWidget(add_btn)
        layout.addLayout(header_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.categories_widget = QWidget()
        self.categories_layout = QVBoxLayout(self.categories_widget)
        self.update_categories_display()

        scroll.setWidget(self.categories_widget)
        layout.addWidget(scroll)

        return widget

    def create_logs_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)

        clear_btn = QPushButton("Clear Logs")
        clear_btn.setObjectName("ClearLogs")
        clear_btn.clicked.connect(self.clear_logs)
        layout.addWidget(clear_btn)

        return widget

    def update_categories_display(self):
        for i in reversed(range(self.categories_layout.count())):
            w = self.categories_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.category_widgets = []
        for category in self.categories:
            widget = CategoryWidget(category)
            self.category_widgets.append(widget)
            self.categories_layout.addWidget(widget)

        self.categories_layout.addStretch()

    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QWidget {
                background-color: #f8f9fa;
                color: #212529;
            }
            QLabel#TitleLabel {
                color: #2c3e50;
                font-size: 28px;
                font-weight: bold;
                margin: 12px;
                background-color: transparent;
            }
            QGroupBox {
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 20px;
                background-color: #ffffff;
                font-weight: bold;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2c3e50;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                color: white;
                background-color: #6c757d;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:disabled {
                background-color: #cbd3da;
                color: #6c757d;
            }
            QPushButton#DryRun {
                background-color: #3498db;
            }
            QPushButton#DryRun:hover {
                background-color: #2980b9;
            }
            QPushButton#Organize {
                background-color: #27ae60;
            }
            QPushButton#Organize:hover {
                background-color: #229954;
            }
            QPushButton#Stop {
                background-color: #e74c3c;
            }
            QPushButton#Stop:hover {
                background-color: #c0392b;
            }
            QPushButton#AddCategory {
                background-color: #2ecc71;
            }
            QPushButton#AddCategory:hover {
                background-color: #27ae60;
            }
            QPushButton#ClearLogs {
                background-color: #95a5a6;
            }
            QPushButton#ClearLogs:hover {
                background-color: #7f8c8d;
            }
            QLineEdit {
                border: 2px solid #ced4da;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                background-color: white;
                color: #212529;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QProgressBar {
                border: 2px solid #ced4da;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                background-color: #e9ecef;
                color: #212529;
                height: 28px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 6px;
            }
            QTabWidget::pane {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background-color: #ffffff;
                top: -2px;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                color: #495057;
                padding: 12px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #dee2e6;
            }
            QTextEdit {
                background-color: #ffffff;
                color: #212529;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
                font-family: Consolas, monospace;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #3498db;
            }
            QStatusBar {
                background-color: #e9ecef;
                color: #495057;
            }
        """)

    # ---------- Event Handlers ----------
    def select_source_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if directory:
            self.source_path.setText(directory)

    def select_dest_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if directory:
            self.dest_path.setText(directory)

    def add_custom_category(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Category")
        dialog.setModal(True)
        dialog.setFixedSize(400, 200)
        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        extensions_edit = QLineEdit()
        extensions_edit.setPlaceholderText("e.g., .txt,.log,.config")
        folder_edit = QLineEdit()

        layout.addRow("Category Name:", name_edit)
        layout.addRow("Extensions:", extensions_edit)
        layout.addRow("Folder Name:", folder_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_edit.text().strip()
            extensions = [ext.strip() for ext in extensions_edit.text().split(',') if ext.strip()]
            folder = folder_edit.text().strip()

            if name and extensions and folder:
                new_category = FileCategory(name, extensions, folder)
                self.categories.append(new_category)
                self.update_categories_display()
                self.add_log(f"Added custom category: {name}")
            else:
                QMessageBox.warning(self, "Invalid Input", "All fields are required!")

    def start_dry_run(self):
        self.start_operation(dry_run=True)

    def start_organization(self):
        reply = QMessageBox.question(
            self, "Confirm Organization",
            "This will move files from your source directory. Are you sure you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.start_operation(dry_run=False)

    def start_operation(self, dry_run=False):
        source_dir = self.source_path.text().strip()
        if not source_dir:
            QMessageBox.warning(self, "No Source Directory", "Please select a source directory!")
            return

        if not Path(source_dir).exists():
            QMessageBox.warning(self, "Invalid Directory", "Source directory does not exist!")
            return

        dest_dir = self.dest_path.text().strip() or None

        self.dry_run_btn.setEnabled(False)
        self.organize_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")

        self.log_text.clear()

        self.worker = FileOrganizerWorker(source_dir, dest_dir, self.categories, dry_run)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.status_updated.connect(self.update_status)
        self.worker.log_updated.connect(self.add_log)
        self.worker.finished.connect(self.on_operation_finished)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def stop_organization(self):
        if self.worker:
            self.worker.stop()
            self.add_log("Stop requested by user.")
            self.stop_btn.setEnabled(False)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def update_status(self, message: str):
        self.status_label.setText(message)
        self.statusBar().showMessage(message)

    def add_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.log_text.append(entry)

    def on_operation_finished(self, summary: dict):
        self.reset_ui_after_operation()

        for widget in self.category_widgets:
            widget.update_count()

        result_lines = [
            f"Organization Summary:",
            f"• Total files scanned: {summary.get('total_files', 0)}",
            f"• Files organized: {summary.get('organized', 0)}",
            f"• Uncategorized files: {summary.get('uncategorized', 0)}",
            "",
            "Files per category:"
        ]

        categories = summary.get('categories', {})
        if categories:
            for cat_name, count in categories.items():
                result_lines.append(f"• {cat_name}: {count} files")
        else:
            result_lines.append("• (none)")

        self.results_label.setText("\n".join(result_lines))

        QMessageBox.information(self, "Operation Complete", f"Processed {summary.get('organized', 0)} files.")

    def on_error(self, error_message: str):
        self.reset_ui_after_operation()
        self.add_log(f"ERROR: {error_message}")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_message}")

    def reset_ui_after_operation(self):
        self.dry_run_btn.setEnabled(True)
        self.organize_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.update_status("Operation complete")

        if self.worker:
            try:
                self.worker.quit()
                self.worker.wait(2000)
            except Exception:
                pass
            self.worker = None

    def clear_logs(self):
        self.log_text.clear()
        self.add_log("Logs cleared.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Operation in Progress",
                "An operation is currently running. Do you want to stop it and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                try:
                    self.worker.quit()
                    self.worker.wait(2000)
                except Exception:
                    pass
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ----------------- MAIN -----------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("File Organizer")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Your Organization")

    window = FileOrganizerGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()