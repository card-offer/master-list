"""Schema 0.3 lives in schema/. This script no longer rewrites it.

Older builds used this file to patch schema 0.2. Running it now would put
verbatim terms clauses back into the published schema, so it does nothing.
"""
import sys

print("schema 0.3 is maintained in schema/. This script does not modify it.")
sys.exit(0)
