import os
import json
import streamlit as st

@st.cache_data
def load_locales():
    """自动读取本地 locales 目录下的所有本地化 JSON 文件"""
    locales = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    locales_dir = os.path.join(base_dir, "locales")
    
    if os.path.exists(locales_dir):
        for file in os.listdir(locales_dir):
            if file.endswith(".json"):
                lang_name = file.split(".")[0]
                with open(os.path.join(locales_dir, file), "r", encoding="utf-8") as f:
                    locales[lang_name] = json.load(f)
    return locales

# 全局单例加载
LOCALES = load_locales()

def _(key: str) -> str:
    """
    核心翻译响应函数。
    读取当前 session_state 里的语言标记，找不到 key 时安全退回 key 本身。
    """
    current_lang = st.session_state.get("lang", "zh")
    lang_dict = LOCALES.get(current_lang, {})
    return lang_dict.get(key, key)