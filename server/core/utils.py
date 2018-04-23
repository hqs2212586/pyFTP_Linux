# -*- coding:utf-8 -*-
__author__ = 'Qiushi Huang'


"""
格式：\033[显示方式;前景色;背景色m
 
说明：
前景色            背景色           颜色
---------------------------------------
30                40              黑色
31                41              红色
32                42              绿色
33                43              黃色
34                44              蓝色
35                45              紫红色
36                46              青蓝色
37                47              白色
显示方式           意义
-------------------------
0                终端默认设置
1                高亮显示
4                使用下划线
5                闪烁
7                反白显示
8                不可见
 
例子：
\033[1;31;40m    <!--1-高亮显示 31-前景色红色  40-背景色黑色-->
\033[0m          <!--采用终端默认设置，即取消颜色设置-->
"""


def print_warning(msg):
    # 033前景色黄色，1是高亮显示，m是背景色默认
    print("\033[33;1mWarning:\033[0m%s" % msg)


def print_error(msg):
    # 031前景色红色，1是高亮显示，m是背景色默认
    print("\033[31;1mError:\033[0m%s" % msg)
