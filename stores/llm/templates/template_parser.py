import os
import importlib.util
from string import Template


class TemplateParser:

    def __init__(self, language: str = None, default_language: str = 'en'):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.language = None
        self.set_language(language)

    def set_language(self, language: str):
        if not language:
            self.language = self.default_language
            return  # ← critical: must return here

        language_path = os.path.join(self.current_path, "locales", language)
        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, vars: dict = None):
        if not group or not key:
            return None

        if vars is None:
            vars = {}

        targeted_language = self.language
        group_path = os.path.join(
            self.current_path, "locales", targeted_language, f"{group}.py"
        )

        if not os.path.exists(group_path):
            targeted_language = self.default_language
            group_path = os.path.join(
                self.current_path, "locales", targeted_language, f"{group}.py"
            )

        if not os.path.exists(group_path):
            return None

        # Load directly from file path — bypasses sys.modules cache entirely
        spec = importlib.util.spec_from_file_location(group, group_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        key_attribute = getattr(module, key, None)

        if key_attribute is None:
            raise ValueError(f"Key '{key}' not found in template module '{group}'")

        if isinstance(key_attribute, Template):
            return key_attribute.substitute(vars)
        elif isinstance(key_attribute, str):
            return key_attribute
        else:
            raise TypeError(
                f"Template key '{key}' must be a string.Template or str, "
                f"got {type(key_attribute)}"
            )