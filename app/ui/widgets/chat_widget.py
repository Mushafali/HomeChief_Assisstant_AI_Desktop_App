from __future__ import annotations
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QFrame,
    QMessageBox,
)

from app.services.gemini_service import GeminiChat
from app.services.async_worker import run_in_thread


class ChatWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.chat: Optional[GeminiChat] = None
        self._init_chat()
        self._threads = []  # list[tuple[QThread, Worker]]

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("Card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 10, 10, 10)
        hl.setSpacing(8)

        title = QLabel("AI Cooking Assistant")
        title.setObjectName("Title")
        hl.addWidget(title)
        hl.addStretch(1)

        self.reset_btn = QPushButton("Reset Chat")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._reset_chat)
        self.reset_btn.setEnabled(self.chat is not None)
        hl.addWidget(self.reset_btn)

        root.addWidget(header)

        # Conversation area
        conv = QFrame()
        conv.setObjectName("Card")
        cl = QVBoxLayout(conv)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(6)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Ask me anything about cooking, ingredients, substitutions, or nutrition...")
        cl.addWidget(self.output, 1)

        row = QHBoxLayout()
        self.input = QPlainTextEdit()
        self.input.setFixedHeight(60)
        row.addWidget(self.input, 1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._send)
        self.send_btn.setEnabled(self.chat is not None)
        row.addWidget(self.send_btn)
        cl.addLayout(row)

        root.addWidget(conv, 1)

        # Info message when AI is disabled
        if self.chat is None:
            info = QLabel("AI chat is disabled. Set GEMINI_API_KEY in your .env and restart the app.")
            info.setObjectName("Subtitle")
            root.addWidget(info)

    def _init_chat(self) -> None:
        try:
            self.chat = GeminiChat()
        except Exception as e:
            print(f"Chat disabled: {e}")
            self.chat = None

    def _reset_chat(self) -> None:
        self._init_chat()
        self.output.clear()
        self.input.clear()
        self.reset_btn.setEnabled(self.chat is not None)
        self.send_btn.setEnabled(self.chat is not None)

    def _send(self) -> None:
        if self.chat is None:
            QMessageBox.warning(self, "AI Unavailable", "Gemini API key is not set. Configure .env and restart.")
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.output.appendPlainText(f"You: {text}")
        self.input.clear()
        # Send in background
        self.send_btn.setEnabled(False)
        old = self.send_btn.text()
        self.send_btn.setText("Sending…")
        thread, worker = run_in_thread(self.chat.send, text)

        def on_result(reply: str):
            msg = reply.strip() or "(No response)"
            self.output.appendPlainText(f"Assistant: {msg}\n")

        worker.result.connect(on_result)

        def on_done():
            self.send_btn.setEnabled(True)
            self.send_btn.setText(old)
            # remove job and clean thread
            to_remove = None
            for job in self._threads:
                if isinstance(job, tuple) and job and job[0] is thread:
                    to_remove = job
                    break
            if to_remove is not None:
                self._threads.remove(to_remove)
            thread.quit()
            thread.wait()

        worker.finished.connect(on_done)
        worker.error.connect(lambda e: QMessageBox.warning(self, "AI Error", str(e)))
        thread.start()
        self._threads.append((thread, worker))
