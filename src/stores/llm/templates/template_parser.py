import os

# it should get default language, error tolerance -> تسامح as if it ask in frence i dont want to get error.
class TemplateParser:

    def __init__(self, language: str=None, default_language='en'):
        self.current_path = os.path.dirname(os.path.abspath(__file__)) # get the directory name from the current file absolute path.
        self.default_language = default_language
        self.language = None

        self.set_language(language)

    
    def set_language(self, language: str):
        if not language:
            self.language = self.default_language

        language_path = os.path.join(self.current_path, "locales", language)
        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, vars: dict={}):
        if not group or not key:
            return None
        
        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py" )
        targeted_language = self.language
        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py" )
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            return None
        
        # import group module
        # duck typing or magic method. -> import during run time the specific language i want.
        module = __import__(f"stores.llm.templates.locales.{targeted_language}.{group}", fromlist=[group]) # fromlist -> i want the group.

        if not module:
            return None
        
        key_attribute = getattr(module, key)
        return key_attribute.substitute(vars) # take the attributes and put them in the key_attribute. without this we will get an error.