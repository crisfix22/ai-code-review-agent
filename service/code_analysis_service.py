"""
Servicio de análisis de código con soporte para múltiples proveedores de IA.
Optimizado para entornos CI/CD y GitHub Actions.
"""
import os
import json
import re
from typing import Optional, Tuple
from pathlib import Path
from openai import OpenAI
import google.generativeai as genai
from anthropic import Anthropic
from dotenv import load_dotenv

from main import logger

load_dotenv()


class CodeAnalysisService:
    """Servicio para análisis de código usando diferentes proveedores de IA."""

    def __init__(self):
        # === Cargar prompts ===
        prompts_path = Path(__file__).parent.parent / "prompts" / "prompts.json"
        if not prompts_path.exists():
            raise FileNotFoundError(f"No se encontró prompts.json en {prompts_path}")
        with open(prompts_path, "r", encoding="utf-8") as f:
            self.prompts = json.load(f)

        # === Inicializar clientes ===
        self.openai_client = None
        self.gemini_client = None
        self.claude_client = None

        if key := os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=key)
        if key := os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=key)
            self.gemini_client = genai
        if key := os.getenv("ANTHROPIC_API_KEY"):
            self.claude_client = Anthropic(api_key=key)

        # === Modelos ===
        self.models = {
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "gemini": os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
            "claude": os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229"),
        }

    # -------------------------------------------------------------------------
    # 🔍 Detección automática de lenguaje
    # -------------------------------------------------------------------------
    def _detect_language_from_diff(self, diff_text: str) -> str:
        """Detecta el lenguaje de programación en base al diff."""
        extensions = set(re.findall(r'\.(\w+)(?=["\'\s]|$)', diff_text))
        python_exts = {"py", "pyi"}
        react_exts = {"jsx", "tsx"}
        js_exts = {"js", "ts"}

        if extensions & python_exts:
            return "python"
        if extensions & react_exts:
            return "react"
        if extensions & js_exts:
            if re.search(r"react(-native)?", diff_text, re.IGNORECASE):
                return "react-native"
            return "javascript"
        return "python"  # fallback seguro

    # -------------------------------------------------------------------------
    # 🧩 Preparar prompt
    # -------------------------------------------------------------------------
    def _get_prompt(self, language: str, title: str, repo: str, author: str, url: str, diff_text: str) -> Tuple[str, str]:
        """Obtiene el prompt adecuado para el lenguaje detectado."""
        language = language.lower()
        prompt_cfg = self.prompts.get(language) or self.prompts.get("python")
        system_prompt = prompt_cfg["system"]
        user_prompt = prompt_cfg["user_template"].format(
            title=title, repo=repo, author=author, url=url, diff_text=diff_text
        )
        return system_prompt, user_prompt

    # -------------------------------------------------------------------------
    # 🤖 Proveedores
    # -------------------------------------------------------------------------
    def _analyze_openai(self, diff_text, title, repo, author, url, language) -> str:
        if not self.openai_client:
            raise RuntimeError("OpenAI no configurado.")
        system_prompt, user_prompt = self._get_prompt(language, title, repo, author, url, diff_text)
        response = self.openai_client.chat.completions.create(
            model=self.models["openai"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    def _analyze_gemini(self, diff_text, title, repo, author, url, language) -> str:
        if not self.gemini_client:
            raise RuntimeError("Gemini no configurado.")
        system_prompt, user_prompt = self._get_prompt(language, title, repo, author, url, diff_text)
        prompt = f"{system_prompt}\n\n{user_prompt}"
        model = genai.GenerativeModel(self.models["gemini"])
        response = model.generate_content(prompt)
        return response.text.strip()

    def _analyze_claude(self, diff_text, title, repo, author, url, language) -> str:
        if not self.claude_client:
            raise RuntimeError("Claude no configurado.")
        system_prompt, user_prompt = self._get_prompt(language, title, repo, author, url, diff_text)
        message = self.claude_client.messages.create(
            model=self.models["claude"],
            system=system_prompt,
            max_tokens=4096,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text.strip()

    # -------------------------------------------------------------------------
    # 🚀 Análisis principal
    # -------------------------------------------------------------------------
    def analyze_code(
        self,
        diff_text: str,
        title: str,
        repo: str,
        author: str,
        url: str,
        provider: str = "auto",
        language: Optional[str] = None,
    ) -> str:
        """Analiza el código usando el proveedor especificado."""
        language = language or self._detect_language_from_diff(diff_text)
        provider = provider.lower()

        # Selección automática de proveedor disponible
        if provider == "auto":
            provider = next(
                (p for p, c in [
                    ("openai", self.openai_client),
                    ("claude", self.claude_client),
                    ("gemini", self.gemini_client),
                ] if c),
                None,
            )
            if not provider:
                logger.error("No hay proveedores de IA configurados")
                raise RuntimeError("No hay proveedores de IA configurados.")
            logger.info(f"🔍 Provider auto-seleccionado: {provider}")

        logger.info(f"📝 Lenguaje detectado: {language}")
        logger.info(f"🤖 Iniciando análisis con provider: {provider} (modelo: {self.models.get(provider, 'N/A')})")

        try:
            if provider == "openai":
                logger.info(f"🔄 Analizando código con OpenAI usando modelo: {self.models['openai']}")
                return self._analyze_openai(diff_text, title, repo, author, url, language)
            if provider == "claude":
                logger.info(f"🔄 Analizando código con Claude usando modelo: {self.models['claude']}")
                return self._analyze_claude(diff_text, title, repo, author, url, language)
            if provider == "gemini":
                logger.info(f"🔄 Analizando código con Gemini usando modelo: {self.models['gemini']}")
                return self._analyze_gemini(diff_text, title, repo, author, url, language)
            raise ValueError(f"Proveedor desconocido: {provider}")
        except Exception as e:
            logger.error(f"❌ Error con provider {provider} (modelo: {self.models.get(provider, 'N/A')}): {e}", exc_info=True)
            # Fallback a OpenAI si hay otra API disponible
            if provider != "openai" and self.openai_client:
                logger.warning(f"⚠️ Fallback a OpenAI (modelo: {self.models['openai']}) debido a error con {provider}")
                return self._analyze_openai(diff_text, title, repo, author, url, language)
            raise
