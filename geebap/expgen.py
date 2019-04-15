# -*- coding: utf-8 -*-
""" Generate expression compatible with Google Earth Engine """
import simpleeval as sval
import ast
import math


class ExpGen(object):
    def __init__(self):
        pass

    @staticmethod
    def max(a, b):
        """ Generates the expression max(a, b) to insert on GEE expression

        :param a: one value to compare
        :param b: the other value to compare
        :return: expression
        :rtype: str
        """

        exp = "({a}>{b}?{a}:{b})".format(a=a, b=b)
        return exp

    @staticmethod
    def min(a, b):
        """ Generates the expression min(a, b) to insert on GEE expression

        :param a: one value to compare
        :param b: the other value to compare
        :return: expression
        :rtype: str
        """

        exp = "({a}<{b}?{a}:{b})".format(a=a, b=b)
        return exp

    @staticmethod
    def parse(expr):
        s = SvalEE()
        return s.eval(expr)


def cat(op, group=True):
    def wrap(a, b):
        if group:
            return "({}{}{})".format(a, op, b)
        else:
            return "{}{}{}".format(a, op, b)
    return wrap


def cat_fun(nom_fun):
    def wrap(arg):
        return "{}({})".format(nom_fun, arg)
    return wrap


def cat_band(band):
    return "b('{}')".format(band)


# CLEAN sval
DEFAULT_NAMES = {"pi": math.pi,
                 "e": math.e}
DEFAULT_FUNCTIONS = {"max": ExpGen.max,
                     "min": ExpGen.min,
                     "b": cat_band,
                     "exp": cat_fun("exp"),
                     "sqrt": cat_fun("sqrt")}
DEFAULT_OPERATORS = {ast.Add: cat("+"),
                     ast.UAdd: lambda a: '+{}'.format(a),
                     ast.Sub: cat("-"),
                     ast.USub: lambda a: '-{}'.format(a),
                     ast.Mult: cat("*"),
                     ast.Div: cat("/"),
                     ast.FloorDiv: cat("//"),
                     ast.Pow: cat("**"),
                     ast.Mod: cat("%"),
                     ast.Eq: cat("=="),
                     ast.NotEq: cat("!="),
                     ast.Gt: cat(">"),
                     ast.Lt: cat("<"),
                     ast.GtE: cat(">="),
                     ast.LtE: cat("<=")}
                     # ast.Not: op.not_,
                     # ast.USub: op.neg,
                     # ast.UAdd: op.pos,
                     # ast.In: lambda x, y: op.contains(y, x),
                     # ast.NotIn: lambda x, y: not op.contains(y, x),
                     # ast.Is: lambda x, y: x is y,
                     # ast.IsNot: lambda x, y: x is not y,}


class SvalEE(sval.SimpleEval):
    def __init__(self, **kwargs):
        super(SvalEE, self).__init__(**kwargs)

        self.operators = DEFAULT_OPERATORS
        self.functions = DEFAULT_FUNCTIONS
        self.names = DEFAULT_NAMES