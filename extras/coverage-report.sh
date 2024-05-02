# Run tests, generate coverage report and open it on a browser
#
# Requires: coverage 3.3 or above from https://pypi.python.org/pypi/coverage

coverage run --branch $(which trial) --reporter=text tests
#!/bin/bash

# Generate coverage report in HTML format and open it in a browser

coverage html -i
python -m webbrowser htmlcov/index.html