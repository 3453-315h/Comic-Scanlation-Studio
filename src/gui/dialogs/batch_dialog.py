
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class BatchProcessDialog(QDialog):
    """Dialog for configuring and running batch processing"""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Batch Process Pages")
        self.resize(500, 600)

        # UI State
        self.is_running = False

        self.setup_ui()
        self.load_pages()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 1. Page Selection
        layout.addWidget(QLabel("Select pages to process:"))
        self.page_list = QListWidget()
        self.page_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.page_list)

        # Buttons to select all/none
        sel_btn_layout = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Select None")
        btn_all.clicked.connect(self.select_all)
        btn_none.clicked.connect(self.select_none)
        sel_btn_layout.addWidget(btn_all)
        sel_btn_layout.addWidget(btn_none)
        layout.addLayout(sel_btn_layout)

        # 2. Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)

        # Parallel toggle
        self.chk_parallel = QCheckBox("Enable Parallel Processing (Experimental)")
        self.chk_parallel.setToolTip("Process multiple pages at once. May use significant CPU/RAM.\n"
                                     "Not recommended if using GPU with low VRAM.")
        config_layout.addWidget(self.chk_parallel)

        # Worker count
        worker_layout = QHBoxLayout()
        worker_layout.addWidget(QLabel("Max Workers:"))
        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, 16)
        self.spin_workers.setValue(2)
        worker_layout.addWidget(self.spin_workers)
        worker_layout.addStretch()
        config_layout.addLayout(worker_layout)

        # Connect toggle to spinner
        self.chk_parallel.toggled.connect(self.spin_workers.setEnabled)
        self.spin_workers.setEnabled(False) # Default off

        layout.addWidget(config_group)

        # 3. Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        layout.addWidget(self.lbl_status)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Start Processing")
        self.btn_run.clicked.connect(self.run_process)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def load_pages(self):
        self.page_list.clear()
        for page in self.project.pages:
            filename = page.file_path.name if hasattr(page.file_path, 'name') else str(page.file_path)
            item = QListWidgetItem(f"Page {page.id}: {filename}")
            item.setData(Qt.UserRole, page.id)
            # Pre-select all
            item.setSelected(True)
            self.page_list.addItem(item)

    def select_all(self):
        for i in range(self.page_list.count()):
            self.page_list.item(i).setSelected(True)

    def select_none(self):
        for i in range(self.page_list.count()):
            self.page_list.item(i).setSelected(False)

    def run_process(self):
        if self.is_running:
            return

        selected_items = self.page_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one page.")
            return

        page_ids = [item.data(Qt.UserRole) for item in selected_items]
        self.pages_to_process = [p for p in self.project.pages if p.id in page_ids]

        # Lock UI
        self.is_running = True
        self.page_list.setEnabled(False)
        self.btn_run.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.pages_to_process))

        # Emit signal to parent or start worker here?
        # Ideally, we return the configuration to the Main Window, which manages the pipeline/thread.
        # But for a modal dialog that SHOWS progress, we often want the thread here or connected here.
        self.accept()
        # Note: We are accept()ing immediately to let MainWindow handle the heavy lifting
        # and create a ProgressDialog or re-use this dialog non-modally.
        # However, typically Batch Dialogs stay open.
        # Let's use the 'done' result to signal MainWindow to start.

    def get_config(self):
        # Ensure pages_to_process is populated if not already
        if not hasattr(self, 'pages_to_process'):
             selected_items = self.page_list.selectedItems()
             page_ids = [item.data(Qt.UserRole) for item in selected_items]
             self.pages_to_process = [p for p in self.project.pages if p.id in page_ids]

        return {
            "pages": self.pages_to_process,
            "parallel": self.chk_parallel.isChecked(),
            "max_workers": self.spin_workers.value()
        }
