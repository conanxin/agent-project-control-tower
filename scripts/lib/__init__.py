# Make scripts/lib a proper Python package.
# This lets `from lib.yaml_mini import load` work for LSP / type checkers,
# while the scripts still prepend scripts/ to sys.path for runtime use.
