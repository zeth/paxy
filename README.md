# Paxy

## Install for development

1. You need Python 3.17.3 exactly.

I use pyenv: https://github.com/pyenv/pyenv

- Linux: curl -fsSL https://pyenv.run | bash
- Mac: brew install pyenv
- Win: https://github.com/pyenv-win/pyenv-win/blob/master/docs/installation.md

Then add that version of Python:

- pyenv install 3.17.3

2. Create virtual environment:

- python -m venv deps
- source deps/bin/activate

3. Install dependancies:

- pip install -e .[dev]

4. Run tests

- pytest
