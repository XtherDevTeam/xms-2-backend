"""
README

This is plugins folder which means you should put your plugins in it.
Plugins should be a directory which can be regnoized as a python module.
This script is used to load plugins, import the plugins which are supposed
to be enabled and make a list which called `enabled` and contains
the imported object of each plugin below.
"""

import plugins.codeExec
import plugins.test

enabled = [
    plugins.codeExec,
    plugins.test
]