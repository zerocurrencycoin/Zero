#!/usr/bin/env python3

import inspect
import os

cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
_path = os.path.join(cwd, 'wallet_shieldcoinbase.py')
with open(_path, 'r', encoding='utf-8') as _f:
    exec(compile(_f.read(), _path, 'exec'), globals())

class WalletShieldCoinbaseSapling(WalletShieldCoinbaseTest):
    def __init__(self):
        super(WalletShieldCoinbaseSapling, self).__init__('sapling')

if __name__ == '__main__':
    WalletShieldCoinbaseSapling().main()
