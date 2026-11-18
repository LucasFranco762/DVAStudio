from __future__ import annotations

from PyQt6.QtCore import QFileInfo, QLibraryInfo, QLocale, QTranslator, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication, QDialogButtonBox, QFileDialog, QFileIconProvider, QGridLayout, QLabel,
    QLineEdit, QListView, QTreeView, QWidget,
)


def install_portuguese_translation() -> None:
    app = QApplication.instance()
    if app is None or app.findChild(QTranslator, "QtPortuguese") is not None:
        return
    QLocale.setDefault(QLocale("pt_BR"))
    translator = QTranslator(app)
    translator.setObjectName("QtPortuguese")
    directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_pt_BR", directory):
        app.installTranslator(translator)
    else:
        translator.deleteLater()


class _PortugueseFileIconProvider(QFileIconProvider):
    def type(self, info: QFileInfo) -> str:
        if info.isRoot():
            return "Unidade"
        if info.isDir():
            return "Pasta"
        suffix = info.suffix().upper()
        return f"Arquivo {suffix}" if suffix else "Arquivo"


class DownloadSaveDialog(QFileDialog):
    def __init__(self, parent: QWidget, directory: str, output_format: str, mode: str):
        install_portuguese_translation()
        super().__init__(parent)
        self._output_format = output_format
        self._name_edited = False
        self._suggested_name = f"download.{output_format}"
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self._icon_provider = _PortugueseFileIconProvider()
        self.setIconProvider(self._icon_provider)
        self.setWindowTitle("Salvar download")
        self.setMinimumSize(780, 520)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setLabelText(QFileDialog.DialogLabel.LookIn, "Salvar em:")
        self.setLabelText(QFileDialog.DialogLabel.FileName, "Nome do arquivo:")
        self.setLabelText(QFileDialog.DialogLabel.FileType, "Tipo de arquivo:")
        self.setLabelText(QFileDialog.DialogLabel.Accept, "Salvar")
        self.setLabelText(QFileDialog.DialogLabel.Reject, "Cancelar")
        kind = "Áudio" if mode == "audio" else "Vídeo"
        self.setNameFilter(f"{kind} {output_format.upper()} (*.{output_format})")
        self.setDefaultSuffix(output_format)
        self.setDirectory(directory)
        self.selectFile(self._suggested_name)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._name_editor = self.findChild(QLineEdit, "fileNameEdit")
        if self._name_editor is not None:
            self._name_editor.textEdited.connect(self._mark_name_edited)
        tree = self.findChild(QTreeView, "treeView")
        if tree is not None:
            tree.header().setStretchLastSection(True)
        sidebar = self.findChild(QListView, "sidebar")
        if sidebar is not None:
            sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        buttons = self.findChild(QDialogButtonBox, "buttonBox")
        if buttons is not None:
            save = buttons.button(QDialogButtonBox.StandardButton.Save)
            if save is not None:
                save.setObjectName("Primary")
                save.setCursor(Qt.CursorShape.PointingHandCursor)
                save.style().unpolish(save)
                save.style().polish(save)
        self._hint = QLabel("Obtendo o nome original do arquivo…", self)
        self._hint.setObjectName("Muted")
        self._hint.setWordWrap(True)
        grid = self.layout()
        if isinstance(grid, QGridLayout):
            grid.addWidget(self._hint, grid.rowCount(), 0, 1, grid.columnCount())

    @pyqtSlot(str)
    def _mark_name_edited(self, text: str) -> None:
        self._name_edited = True

    @pyqtSlot(str)
    def set_original_name(self, name: str) -> None:
        if (not self._name_edited and self._name_editor is not None
                and self._name_editor.text() == self._suggested_name):
            suffix = f".{self._output_format}"
            stem = name[:-len(suffix)] if name.lower().endswith(suffix) else name
            self._suggested_name = stem + suffix
            self._name_editor.setText(self._suggested_name)
            self._name_editor.setSelection(0, len(stem))
        self._hint.setText("Você pode alterar o nome do arquivo e a pasta antes de salvar.")

    @pyqtSlot(str)
    def name_unavailable(self, message: str) -> None:
        self._hint.setText("Não foi possível obter o nome original. Informe o nome desejado antes de salvar.")
