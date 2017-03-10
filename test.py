# -*- coding: utf-8 -*-
"""

@author: Rem
@contack: remch183@outlook.com
@time: 2017/03/10/ 17:12 
"""

__author__ = "Rem"

import maker
import os

if __name__ == '__main__':
    m = maker.ExpressionMaker()
    root = './input/'
    for file in os.listdir(root):
        if file != 'demo.jpg': continue
        try:
            m.make_expression(root + file)
        except BaseException:
            pass

