#!/usr/bin/env python
# -*- coding:utf-8 -*- 
import random
import itertools
import base64
import binascii
from gmssl import sm3, func

#定义一部分基本运算
xor = lambda a, b:list(map(lambda x, y: x ^ y, a, b))
rotl = lambda x, n:((x << n) & 0xffffffff) | ((x >> (32 - n)) & 0xffffffff)
get_uint32_be = lambda key_data:((key_data[0] << 24) | (key_data[1] << 16) | (key_data[2] << 8) | (key_data[3]))
put_uint32_be = lambda n:[((n>>24)&0xff), ((n>>16)&0xff), ((n>>8)&0xff), ((n)&0xff)]
padding = lambda data, block=16: data + [(16 - len(data) % block)for _ in range(16 - len(data) % block)]
unpadding = lambda data: data[:-data[-1]]
list_to_bytes = lambda data: b''.join([bytes((i,)) for i in data])
bytes_to_list = lambda data: [i for i in data]
random_hex = lambda x: ''.join([choice('0123456789abcdef') for _ in range(x)])

#初值IV
IV = [
    1937774191, 1226093241, 388252375, 3666478592,
    2842636476, 372324522, 3817729613, 2969243214,
]

T_j = [
    2043430169, 2043430169, 2043430169, 2043430169, 2043430169, 2043430169,
    2043430169, 2043430169, 2043430169, 2043430169, 2043430169, 2043430169,
    2043430169, 2043430169, 2043430169, 2043430169, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042, 2055708042, 2055708042,
    2055708042, 2055708042, 2055708042, 2055708042
]

#FF
def FF(x, y, z, j):
    if 0 <= j and j < 16:
        m = x ^ y ^ z
    elif 16 <= j and j < 64:
        m = (x & y) | (x & z) | (y & z)
    return m

#GG
def GG(x, y, z, j):
    if 0 <= j and j < 16:
        m = x ^ y ^ z
    elif 16 <= j and j < 64:
        m = (x & y) | ((~ x) & z)
    return m

def p_0(x):
    return x ^ (rotl(x, 9 % 32)) ^ (rotl(x, 17 % 32))

def p_1(x):
    return x ^ (rotl(x, 15 % 32)) ^ (rotl(x, 23 % 32))

#sm3迭代压缩
def sm3_cf(v_i, b_i):
    w = []
    for i in range(16):
        weight = 0x1000000
        data = 0
        for k in range(i*4,(i+1)*4):
            data = data + b_i[k]*weight
            weight = int(weight/0x100)
        w.append(data)

    for j in range(16, 68):
        w.append(0)
        w[j] = sm3_p_1(w[j-16] ^ w[j-9] ^ (rotl(w[j-3], 15 % 32))) ^ (rotl(w[j-13], 7 % 32)) ^ w[j-6]
        str1 = "%08x" % w[j]
    w_1 = []
    for j in range(0, 64):
        w_1.append(0)
        w_1[j] = w[j] ^ w[j+4]
        str1 = "%08x" % w_1[j]

    a, b, c, d, e, f, g, h = v_i

    for j in range(0, 64):
        ss_1 = rotl(
            ((rotl(a, 12 % 32)) +
            e +
            (rotl(T_j[j], j % 32))) & 0xffffffff, 7 % 32
        )
        ss_2 = ss_1 ^ (rotl(a, 12 % 32))
        tt_1 = (FF(a, b, c, j) + d + ss_2 + w_1[j]) & 0xffffffff
        tt_2 = (GG(e, f, g, j) + h + ss_1 + w[j]) & 0xffffffff
        d = c
        c = rotl(b, 9 % 32)
        b = a
        a = tt_1
        h = g
        g = rotl(f, 19 % 32)
        f = e
        e = sm3_p_0(tt_2)

        a, b, c, d, e, f, g, h = map(
            lambda x:x & 0xFFFFFFFF ,[a, b, c, d, e, f, g, h])

    v_j = [a, b, c, d, e, f, g, h]
    return [v_j[i] ^ v_i[i] for i in range(8)]
def sm3_hash(msg, new_v):
    len1 = len(msg)
    reserve1 = len1 % 64
    msg.append(0x80)
    reserve1 = reserve1 + 1
    range_end = 56
    if reserve1 > range_end:
        range_end = range_end + 64

    for i in range(reserve1, range_end):
        msg.append(0x00)

    bit_length = (len1) * 8
    bit_length_str = [bit_length % 0x100]
    for i in range(7):
        bit_length = int(bit_length / 0x100)
        bit_length_str.append(bit_length % 0x100)
    for i in range(8):
        msg.append(bit_length_str[7-i])

    group_count = round(len(msg) / 64) - 1

    B = []
    for i in range(0, group_count):
        B.append(msg[(i + 1)*64:(i+2)*64])

    V = []
    V.append(new_v)
    for i in range(0, group_count):
        V.append(sm3_cf(V[i], B[i]))

    y = V[i+1]
    result = ""
    for i in y:
        result = '%s%08x' % (result, i)
    return result


alphatable = "abcdefghigklmnopqrstuvwxyz"
def randomstr(randomlength=8):
  random_str =''
  base_str ='abcdefghigklmnopqrstuvwxyz'
  length = len(base_str) -1
  for i in range(randomlength):
    random_str += base_str[random.randint(0, length)]
  return random_str
#查找并加入,num为攻击次数，length为字符串长度

def attack(num,length = 6):
    hashmap={}
    alphatable = "abcdefghijklmnopqrstuvwxyz"
    i = 0
    for s in itertools.permutations(alphatable,length):
        i+=1
        strs=""
        for k in range(length):
            strs+=s[k]
        data = bytes(strs, encoding='utf-8')
        #切片大小界定碰撞长度
        sign = sm3.sm3_hash(func.bytes_to_list(data))[:7]
        if sign in hashmap:
          print("success")
          return (hashmap[sign],strs)
        else:
            hashmap[sign]=strs
        if i>=num:
            break
    print("fail")
    return (0, 0)

print(attack(pow(2,16),8))
