#!/usr/bin/env python2
import json, sys

elitehrv = json.load(open(sys.argv[1]))

for entry in elitehrv['entries']:
    if len(sys.argv) < 3:
        print(entry['datetime'])
    elif entry['datetime'].startswith(sys.argv[2]):
        print("\n".join(entry['rrs'].split(',')))
        sys.exit(0)
sys.exit(1)
