# Run tests, generate coverage report and open it on a browser
#!/bin/bash
#
# Script to generate a coverage report for Python code
# Requires: coverage 3.3 or above from https://pypi.python.org/pypi/coverage

# Run coverage with branch coverage enabled
coverage run --branch $(which trial) --reporter=text tests

# Generate HTML coverage report
coverage html -i

# Open the HTML coverage report in a web browser
python -m webbrowser htmlcov/index.html
