# Run tests, generate coverage report and open it on a browser
#
# Requires: coverage 3.3 or above from https://pypi.python.org/pypi/coverage

coverage run --branch /path/to/trial --reporter=text tests
coverage html -i
python -m webbrowser htmlcov/index.html