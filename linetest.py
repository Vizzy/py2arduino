#!/usr/bin/env python3.3

import sys, pprint
from pyduino import translate

pp = pprint.PrettyPrinter()

input_code = sys.argv[1]

result = translate(input_code)

pp.pprint(result)
print(result['code'])
