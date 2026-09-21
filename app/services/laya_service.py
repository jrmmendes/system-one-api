import os
from typing import Any

os.environ["USE_TF"] = "0"

from laya import Router, clean_email_body


class LayaService:
    _instance: "LayaService | None" = None
    _router: Router | None = None

    def __new__(cls) -> "LayaService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, device: str = "cpu") -> None:
        if self._router is None:
            self._router = Router(preload=True, device=device)

    @property
    def router(self) -> Router:
        if self._router is None:
            raise RuntimeError("LayaService not initialized. Call initialize() first.")
        return self._router

    @staticmethod
    def sanitize(text: str) -> str:
        return clean_email_body(text)

    @staticmethod
    def _to_laya_format(questions: dict[str, Any]) -> dict[str, Any]:
        laya_questions = {}
        for qid, q in questions.items():
            t = q["type"]
            if t == "choice":
                options = q["options"]
                if isinstance(options, list):
                    criteria = {opt: None for opt in options}
                else:
                    criteria = options
                laya_questions[qid] = {
                    "type": "choice",
                    "instructions": "",
                    "criteria": criteria,
                }
            elif t == "noul":
                criteria = {}
                if q.get("true_criteria"):
                    criteria["true"] = q["true_criteria"]
                if q.get("false_criteria"):
                    criteria["false"] = q["false_criteria"]
                laya_questions[qid] = {
                    "type": "noul",
                    "instructions": q["instruction"],
                    "criteria": criteria or None,
                }
            elif t == "score":
                laya_questions[qid] = {
                    "type": "score",
                    "instructions": q["instruction"],
                    "criteria": q.get("levels", []),
                }
        return laya_questions

    def predict(self, text: str, questions: dict[str, Any]) -> dict[str, Any]:
        state = {"body": self.sanitize(text)}
        laya_questions = self._to_laya_format(questions)
        return self.router.predict(state=state, questions=laya_questions)


def get_laya_service() -> LayaService:
    return LayaService()
