#!/usr/bin/env python
#-*- coding:utf-8 -*-
# author:

a ='001010101'
b = int(a,2)
# print(b)

s = str(bin(-16))
print(s)
if s.count('1') == 1:
    # print('true')
    pass
else:
    # print('false')
    pass
def gen(x):
    y = abs(27)
    while y > 0:
        yield y % 3
        y = y >> 1
    else:
        if x == 0: yield 0
    l = [ i for i in gen(x)]
    l.reverse()
    if x >= 0:
        print ('%d' * len(l) % tuple(l))
    else:
        print('-' + ('%d'* len(l) % tuple(l)))



