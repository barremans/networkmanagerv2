# =============================================================================
# Networkmap_Creator
# File:    app/helpers/uppercase_filter.py
# Role:    Globale eventfilter — alle QLineEdit invoer automatisch naar uppercase
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                  QApplication eventfilter op KeyPress
#          1.1.0 — FocusIn + Show: bestaande waarden ook naar uppercase
#          1.2.0 — QTextEdit (notities) ook naar uppercase
#                  Werkt op alle QLineEdit velden in de hele app
#                  Geen aanpassingen nodig in individuele dialogen
# =============================================================================

from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QLineEdit, QTextEdit


class UpperCaseFilter(QObject):
    """
    Globale eventfilter die alle tekst in QLineEdit velden
    automatisch naar uppercase converteert.

    Installeren via:
        from app.helpers.uppercase_filter import UpperCaseFilter
        _uc_filter = UpperCaseFilter(app)
        app.installEventFilter(_uc_filter)
    """

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if isinstance(obj, (QLineEdit, QTextEdit)):

            # Bij focus of tonen: bestaande waarde naar uppercase converteren
            if event.type() in (
                QEvent.Type.FocusIn,
                QEvent.Type.Show,
                QEvent.Type.Polish,
            ):
                if isinstance(obj, QTextEdit):
                    current = obj.toPlainText()
                    upper   = current.upper()
                    if current != upper:
                        obj.setPlainText(upper)
                        cursor = obj.textCursor()
                        cursor.movePosition(cursor.MoveOperation.End)
                        obj.setTextCursor(cursor)
                else:
                    current = obj.text()
                    upper   = current.upper()
                    if current != upper:
                        cursor_pos = obj.cursorPosition()
                        obj.setText(upper)
                        obj.setCursorPosition(cursor_pos)
                return False  # event verder laten passeren

            # Bij typen: nieuwe toetsaanslag naar uppercase
            if event.type() == QEvent.Type.KeyPress:
                from PySide6.QtCore import Qt
                key = event.key()
                if key < Qt.Key.Key_Space:
                    return False

                text = event.text()
                if text and text != text.upper():
                    from PySide6.QtGui import QKeyEvent
                    upper_event = QKeyEvent(
                        event.type(),
                        key,
                        event.modifiers(),
                        text.upper(),
                    )
                    if isinstance(obj, QTextEdit):
                        QTextEdit.keyPressEvent(obj, upper_event)
                    else:
                        QLineEdit.keyPressEvent(obj, upper_event)
                    return True

        return False