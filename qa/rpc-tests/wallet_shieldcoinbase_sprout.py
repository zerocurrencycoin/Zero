#!/usr/bin/env python3

import inspect
import os

cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
_path = os.path.join(cwd, 'wallet_shieldcoinbase.py')
with open(_path, 'r', encoding='utf-8') as _f:
    exec(compile(_f.read(), _path, 'exec'), globals())

class WalletShieldCoinbaseSprout(WalletShieldCoinbaseTest):
    def __init__(self):
        super(WalletShieldCoinbaseSprout, self).__init__('sprout')

if __name__ == '__main__':
    WalletShieldCoinbaseSprout().main()
