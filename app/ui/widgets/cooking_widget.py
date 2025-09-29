from __future__ import annotations
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
)

from app.models.recipe import Recipe
from app.services.gemini_service import GeminiService
from app.services.async_worker import run_in_thread


class CookingWidget(QWidget):
    def __init__(self, gemini: Optional[GeminiService]) -> None:
        super().__init__()
        self.gemini = gemini
        self.recipe: Optional[Recipe] = None
        self.step_index: int = 0
        self._threads = []  # list[tuple[QThread, Worker]]

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("Card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 10, 10, 10)
        hl.setSpacing(8)

        self.title_lbl = QLabel("Cooking Guide")
        self.title_lbl.setObjectName("Title")
        hl.addWidget(self.title_lbl)

        hl.addStretch(1)

        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self._prev)
        hl.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._next)
        hl.addWidget(self.next_btn)

        self.tip_btn = QPushButton("Ask AI Tip")
        self.tip_btn.clicked.connect(self._ask_tip)
        self.tip_btn.setEnabled(self.gemini is not None)
        hl.addWidget(self.tip_btn)

        root.addWidget(header)

        # Step content
        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 10, 10, 10)
        cl.setSpacing(8)

        self.step_meta = QLabel("")
        self.step_meta.setObjectName("Subtitle")
        cl.addWidget(self.step_meta)

        self.step_text = QLabel("Open a recipe and press Start Cooking.")
        self.step_text.setWordWrap(True)
        cl.addWidget(self.step_text)

        root.addWidget(card, 1)

    def set_recipe(self, recipe: Recipe) -> None:
        self.recipe = recipe
        self.step_index = 0
        self.title_lbl.setText(f"Cooking: {recipe.title}")
        self._render_step()

    def _render_step(self) -> None:
        if not self.recipe or not self.recipe.steps:
            self.step_meta.setText("")
            self.step_text.setText("This recipe has no steps.")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.tip_btn.setEnabled(self.gemini is not None and self.recipe is not None)
            return
        total = len(self.recipe.steps)
        self.step_index = max(0, min(self.step_index, total - 1))
        self.step_meta.setText(f"Step {self.step_index + 1} of {total}")
        self.step_text.setText(self.recipe.steps[self.step_index])
        self.prev_btn.setEnabled(self.step_index > 0)
        self.next_btn.setEnabled(self.step_index < total - 1)
        self.tip_btn.setEnabled(self.gemini is not None)

    def _prev(self) -> None:
        self.step_index -= 1
        self._render_step()

    def _next(self) -> None:
        self.step_index += 1
        self._render_step()

    def _ask_tip(self) -> None:
        if self.gemini is None:
            QMessageBox.warning(self, "AI Unavailable", "Gemini API key is not set. Configure .env and restart.")
            return
        if not self.recipe or not self.recipe.steps:
            return
        step_text = self.recipe.steps[self.step_index]
        question = (
            "Provide a concise, practical tip for executing the current step safely and effectively."
        )
        context = f"Recipe: {self.recipe.title}\nCurrent Step: {step_text}"
        # Run in background
        self.tip_btn.setEnabled(False)
        old = self.tip_btn.text()
        self.tip_btn.setText("Asking…")
        thread, worker = run_in_thread(self.gemini.answer, question, context)

        def on_result(ans: str):
            msg = ans.strip() or "No tip available."
            QMessageBox.information(self, "AI Tip", msg)

        worker.result.connect(on_result)

        def on_done():
            self.tip_btn.setEnabled(True)
            self.tip_btn.setText(old)
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
