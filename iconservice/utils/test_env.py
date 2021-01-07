# -*- coding: utf-8 -*-

__under_testing = False


def is_under_testing() -> bool:
    return __under_testing


def start_testing():
    global __under_testing
    __under_testing = True
