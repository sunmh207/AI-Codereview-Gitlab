import gettext
import os
from typing import Callable

from dotenv import load_dotenv

load_dotenv("conf/.env")


def init_language(lang_code=None) -> Callable[[str], str]:
    if lang_code is None:
        lang_code = os.environ.get('LANGUAGE', 'zh_CN')
        print(f"Using language: {lang_code}")
    lang = gettext.translation("messages", localedir="locales", languages=[lang_code], fallback=True)
    lang.install()
    global _
    _ = lang.gettext
    return _


def get_translator() -> Callable[[str], str]:
    return _


init_language()
