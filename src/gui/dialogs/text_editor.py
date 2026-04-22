from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QDialogButtonBox, QHeaderView, QLabel, QHBoxLayout, QPushButton, QApplication
)
from PySide6.QtCore import Qt
from typing import List, Callable, Optional
from ...core.project import TextBubble

class TextEditorDialog(QDialog):
    """
    Dialog for editing detected text and translations in a table view.
    """
    def __init__(self, bubbles: List[TextBubble], parent=None, translator_callback: Optional[Callable[[str], str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Text & Translations")
        self.resize(900, 600)
        self.bubbles = bubbles
        self.translator_callback = translator_callback
        # Filter strictly for bubbles that are not failed
        self.valid_bubbles = [b for b in bubbles if b.status != 'failed']
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        info = QLabel("Double-click cells to edit text. Changes will be applied for Translation and Imprinting steps.")
        info.setStyleSheet("color: #8c8d8e; margin-bottom: 8px;")
        layout.addWidget(info)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Original Text (OCR)", "Translated Text", "Google Translate"])
        
        # Setup Header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Original
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Translated
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # Google
        
        self.table.setRowCount(len(self.valid_bubbles))
        
        for i, bubble in enumerate(self.valid_bubbles):
            # ID Column (Read-only)
            id_item = QTableWidgetItem(str(i + 1))
            id_item.setFlags(id_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, id_item)
            
            # Original Text
            orig_text = bubble.text_original or ""
            item_orig = QTableWidgetItem(orig_text)
            self.table.setItem(i, 1, item_orig)
            
            # Translated Text
            trans_text = bubble.text_translated or ""
            item_trans = QTableWidgetItem(trans_text)
            self.table.setItem(i, 2, item_trans)

            # Google Translate (Ephemeral, Read-only initially)
            item_google = QTableWidgetItem("")
            item_google.setFlags(item_google.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 3, item_google)
            
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.btn_translate = QPushButton("Translate Selected")
        self.btn_translate.clicked.connect(lambda: self.translate_selected_rows(engine=None))
        button_layout.addWidget(self.btn_translate)
        
        self.btn_google = QPushButton("Translate with Google")
        self.btn_google.clicked.connect(lambda: self.translate_selected_rows(engine="google"))
        button_layout.addWidget(self.btn_google)

        self.btn_apply_google = QPushButton("Use Google Result")
        self.btn_apply_google.setToolTip("Apply Google translation to selected rows")
        self.btn_apply_google.clicked.connect(self.apply_google_translation)
        button_layout.addWidget(self.btn_apply_google)
        
        button_layout.addStretch()
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        button_layout.addWidget(buttons)
        
        layout.addLayout(button_layout)

    def translate_selected_rows(self, engine: str = None):
        """Translate selected rows using the callback
        
        Args:
            engine: Optional translation engine override (e.g. "google")
        """
        if not self.translator_callback:
            return
            
        # Get rows from any selected cells
        selected_indexes = self.table.selectionModel().selectedIndexes()
        if not selected_indexes:
            # If no rows are selected, translate ALL rows by default
            selected_rows = list(range(self.table.rowCount()))
        else:
            selected_rows = sorted(set(index.row() for index in selected_indexes))
            
        # Optional: Show progress or disable button
        self.btn_translate.setEnabled(False)
        self.btn_translate.setText("Translating...")
        QApplication.processEvents()
        
        try:
            for row in selected_rows:
                # Get original text
                item_orig = self.table.item(row, 1)
                text = item_orig.text() if item_orig else ""
                
                if text:
                    # Pass engine to callback (requires callback update in main_window)
                    # We assume callback signature is now (text, engine=None)
                    # Determine target column
                    target_col = 3 if engine == "google" else 2

                    try:
                        translated = self.translator_callback(text, engine=engine)
                    except TypeError:
                        # Fallback for old signature if not updated
                        translated = self.translator_callback(text)
                        
                    if translated:
                        self.table.setItem(row, target_col, QTableWidgetItem(translated))
        finally:
            self.btn_translate.setEnabled(True)
            self.btn_translate.setText("Translate Selected")

    def on_cell_double_clicked(self, row, column):
        """Handle double clicks on cells."""
        # If double clicking Google column (3), copy to Translated column (2)
        if column == 3:
            item = self.table.item(row, column)
            if item and item.text():
                self.table.setItem(row, 2, QTableWidgetItem(item.text()))
    
    def apply_google_translation(self):
        """Apply Google translation to the main translation column for selected rows."""
        selected_indexes = self.table.selectionModel().selectedIndexes()
        if not selected_indexes:
            return
            
        selected_rows = sorted(set(index.row() for index in selected_indexes))
        
        for row in selected_rows:
            google_item = self.table.item(row, 3)
            if google_item and google_item.text():
                self.table.setItem(row, 2, QTableWidgetItem(google_item.text()))

    def save_changes(self):
        """Write table contents back to bubble objects"""
        for i, bubble in enumerate(self.valid_bubbles):
            # Update Original
            new_orig = self.table.item(i, 1).text()
            if bubble.text_original != new_orig:
                bubble.text_original = new_orig
                # If we change original, we might want to reset status if it was translated? 
                # For now let's just update it.
            
            # Update Translated
            new_trans = self.table.item(i, 2).text()
            if bubble.text_translated != new_trans:
                bubble.text_translated = new_trans
                if not bubble.status == "translated" and new_trans:
                     bubble.status = "translated" 
