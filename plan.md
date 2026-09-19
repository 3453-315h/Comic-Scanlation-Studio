1. **Refactor `Translator` class in `src/modules/translator.py`**
   - Use `replace_with_git_merge_diff` to modify `src/modules/translator.py`:
     - In `__init__`, add `self._requests_session = requests.Session()` and `self._openai_client = None`.
     - In `_deepl_translate`, change `requests.post` to `self._requests_session.post`.
     - In `_openai_translate`, instantiate `OpenAI` client once and save it to `self._openai_client` if it is `None`, then reuse it.
2. **Verify File Modifications**
   - Run `sed -n '66,105p' src/modules/translator.py` to confirm the changes to `__init__`.
   - Run `sed -n '228,249p' src/modules/translator.py` to confirm the changes to `_deepl_translate`.
   - Run `sed -n '250,285p' src/modules/translator.py` to confirm the changes to `_openai_translate`.
3. **Verify Code Correctness**
   - Run `PYTHONPATH=. pytest` (if tests exist), `mypy src/`, and `ruff check src/` to ensure no syntax errors or typing issues were introduced.
4. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**
5. **Submit PR**
   - Title: "⚡ Bolt: Reuse HTTP clients for API translations"
   - Description containing 💡 What, 🎯 Why, 📊 Impact, 🔬 Measurement.
