How to build the documentation?

1. Install the doc package:
```bash
cd doc
poetry install
```

2. Build the documentation:
```bash
poetry run make html
```

This will generate the documentation in the `doc/build/html` directory.
The documentation can be viewed by opening the `index.html` file in a web browser.