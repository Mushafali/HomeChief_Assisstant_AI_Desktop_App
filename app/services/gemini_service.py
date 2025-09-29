from __future__ import annotations
import json
import traceback
from typing import Any, Dict, List, Optional
import re

import google.generativeai as genai

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.models.recipe import Recipe


class GeminiService:
    """Wrapper around Google Gemini for one-off generations.

    Provides utility methods to:
    - Suggest recipes from ingredients with structured JSON output
    - Suggest substitutions for a given recipe
    - Ask general questions with optional context
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set. Put it in your .env file.")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model_name = model_name or GEMINI_MODEL or "gemini-1.5-flash"
        # Try preferred model, then fallbacks on NotFound
        try:
            self.model = genai.GenerativeModel(self.model_name)
        except Exception as e:
            if self._is_not_found(e):
                for name in self._FALLBACK_MODELS:
                    try:
                        self.model = genai.GenerativeModel(name)
                        self.model_name = name
                        break
                    except Exception:
                        continue
                else:
                    raise
            else:
                raise

    # --- internal helpers for resiliency ---
    _FALLBACK_MODELS = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro-002",
    ]

    def _is_not_found(self, e: Exception) -> bool:
        msg = str(e)
        return ("NotFound" in msg) or ("404" in msg) or ("not found" in msg.lower())

    def _try_switch_model(self) -> bool:
        for name in self._FALLBACK_MODELS:
            if name == self.model_name:
                continue
            try:
                self.model = genai.GenerativeModel(name)
                self.model_name = name
                return True
            except Exception:
                continue
        return False

    def _generate_json(self, prompt: str, fallback_key: str = "text") -> Dict[str, Any]:
        def request_json() -> Dict[str, Any]:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_output_tokens": 1024,
                    "response_mime_type": "application/json",
                },
            )
            txt = (response.text or "{}").strip()
            # Try direct parse
            try:
                return json.loads(txt)
            except Exception:
                # Remove common code fences and retry
                cleaned = re.sub(r"^```(?:json)?\s*|```$", "", txt, flags=re.IGNORECASE | re.MULTILINE).strip()
                try:
                    return json.loads(cleaned)
                except Exception:
                    # Extract the first top-level JSON object if present
                    start = cleaned.find("{")
                    end = cleaned.rfind("}")
                    if start != -1 and end != -1 and end > start:
                        candidate = cleaned[start : end + 1]
                        return json.loads(candidate)
                    raise

        try:
            return request_json()
        except Exception as e:
            # If model is not found, try switching once and retry JSON request
            if self._is_not_found(e) and self._try_switch_model():
                try:
                    return request_json()
                except Exception as e2:
                    # Continue to fallback path below
                    e = e2
            # Fallback to non-JSON response (single attempt)
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "max_output_tokens": 1024,
                    },
                )
                return {fallback_key: response.text or ""}
            except Exception as e3:
                traceback.print_exc()
                # Propagate so UI can show an error dialog
                raise e3

    def suggest_from_ingredients(self, ingredients: List[str], db_recipes: List[Recipe]) -> Dict[str, Any]:
        """Return structured suggestions based on ingredients.

        Output schema (best effort):
        {
          "match_titles": ["Spaghetti Aglio e Olio", ...],
          "ideas": [
            {
              "title": "...",
              "description": "...",
              "ingredients": [{"name": "...", "quantity": "..."}],
              "steps": ["..."],
              "time_minutes": 0,
              "difficulty": "Easy|Medium|Hard",
              "categories": ["...", "..."]
            }
          ],
          "substitutions": ["If missing butter, use oil", ...]
        }
        """
        ingredient_list = ", ".join(sorted(set(i.strip() for i in ingredients if i.strip())))
        catalog = [
            {
                "title": r.title,
                "ingredients": [ing.get("name", "") for ing in r.ingredients],
                "time_minutes": r.time_minutes,
                "difficulty": r.difficulty,
                "categories": r.categories,
            }
            for r in db_recipes
        ]
        sys_prompt = (
            "You are HomeChef AI. You match user ingredients to known recipes and create new ideas if needed. "
            "Only return valid JSON matching the requested schema."
        )
        user_prompt = f"""
System: {sys_prompt}
User Ingredients: {ingredient_list}
Catalog: {json.dumps(catalog, ensure_ascii=False)}

Return JSON with keys: match_titles (array of titles from Catalog), ideas (array of new recipe objects), substitutions (array of strings).
Ensure all fields exist. Set reasonable defaults if unknown.
"""
        data = self._generate_json(user_prompt, fallback_key="raw")
        # Validate/normalize
        match_titles = [str(t) for t in data.get("match_titles", [])][:20]
        ideas_raw = data.get("ideas", [])
        ideas: List[Dict[str, Any]] = []
        for idea in ideas_raw[:10]:
            try:
                ideas.append(
                    {
                        "title": str(idea.get("title", "AI Idea"))[:120],
                        "description": str(idea.get("description", ""))[:2000],
                        "ingredients": [
                            {
                                "name": str(i.get("name", ""))[:120],
                                "quantity": str(i.get("quantity", ""))[:120],
                            }
                            for i in idea.get("ingredients", [])
                            if str(i.get("name", "")).strip()
                        ],
                        "steps": [str(s) for s in idea.get("steps", [])][:30],
                        "time_minutes": int(idea.get("time_minutes", 0) or 0),
                        "difficulty": str(idea.get("difficulty", "Easy"))[:20],
                        "categories": [str(c) for c in idea.get("categories", [])][:10],
                    }
                )
            except Exception:
                continue
        substitutions = [str(s) for s in data.get("substitutions", [])][:20]
        return {"match_titles": match_titles, "ideas": ideas, "substitutions": substitutions}

    def substitutions_for_recipe(self, recipe: Recipe, missing_ingredients: List[str]) -> List[str]:
        prompt = f"""
You are HomeChef AI. Provide practical, safe ingredient substitutions specific to this recipe.
Recipe Title: {recipe.title}
Missing Ingredients: {', '.join(missing_ingredients)}
Ingredients: {json.dumps(recipe.ingredients, ensure_ascii=False)}

Return a numbered list with short, actionable substitutions.
"""
        try:
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.4,
                        "top_p": 0.9,
                        "max_output_tokens": 512,
                    },
                )
            except Exception as e:
                if self._is_not_found(e) and self._try_switch_model():
                    response = self.model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.4,
                            "top_p": 0.9,
                            "max_output_tokens": 512,
                        },
                    )
                else:
                    raise
            text = response.text or ""
            lines = [l.strip(" -*\t") for l in text.splitlines() if l.strip()]
            return [l for l in lines if any(ch.isalpha() for ch in l)][:20]
        except Exception as e:
            traceback.print_exc()
            raise e

    def answer(self, question: str, context: Optional[str] = None) -> str:
        prompt = f"Context: {context}\nQuestion: {question}" if context else question
        try:
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.5,
                        "top_p": 0.9,
                        "max_output_tokens": 512,
                    },
                )
            except Exception as e:
                if self._is_not_found(e) and self._try_switch_model():
                    response = self.model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.5,
                            "top_p": 0.9,
                            "max_output_tokens": 512,
                        },
                    )
                else:
                    raise
            return response.text or ""
        except Exception as e:
            traceback.print_exc()
            raise e


class GeminiChat:
    """Stateful chat session with Gemini for the Chat widget."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set. Put it in your .env file.")
        genai.configure(api_key=GEMINI_API_KEY)
        model_name = model_name or GEMINI_MODEL or "gemini-1.5-flash"
        # Try preferred model, then fallbacks on NotFound
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            msg = str(e)
            if ("NotFound" in msg) or ("404" in msg) or ("not found" in msg.lower()):
                for name in [
                    "gemini-1.5-flash-latest",
                    "gemini-1.5-flash-002",
                    "gemini-1.5-flash-8b",
                    "gemini-1.5-pro-002",
                ]:
                    try:
                        model = genai.GenerativeModel(name)
                        break
                    except Exception:
                        continue
                else:
                    raise
            else:
                raise
        self.model = model
        self.chat = self.model.start_chat(history=[])

    def send(self, message: str) -> str:
        try:
            try:
                resp = self.chat.send_message(
                    message,
                    generation_config={
                        "temperature": 0.5,
                        "top_p": 0.9,
                        "max_output_tokens": 768,
                    },
                )
            except Exception as e:
                # Attempt to switch to a working chat model and retry once
                msg = str(e)
                if ("NotFound" in msg) or ("404" in msg) or ("not found" in msg.lower()):
                    # Recreate underlying model and chat with fallback names
                    for name in [
                        "gemini-1.5-flash-latest",
                        "gemini-1.5-flash-002",
                        "gemini-1.5-flash-8b",
                        "gemini-1.5-pro-002",
                    ]:
                        try:
                            model = genai.GenerativeModel(name)
                            self.model = model
                            self.chat = model.start_chat(history=[])
                            resp = self.chat.send_message(
                                message,
                                generation_config={
                                    "temperature": 0.5,
                                    "top_p": 0.9,
                                    "max_output_tokens": 768,
                                },
                            )
                            break
                        except Exception:
                            continue
                    else:
                        raise
                else:
                    raise
            return resp.text or ""
        except Exception as e:
            traceback.print_exc()
            raise e
