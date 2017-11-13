#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Modulo para generar expresiones compatibles con GEE """
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


def cat(op, agrupar=True):
    def wrap(a, b):
        if agrupar:
            return "("+str(a)+str(op)+str(b)+")"
        else:
            return str(a)+str(op)+str(b)
    return wrap

def cat_fun(nom_fun):
    def wrap(arg):
        return str(nom_fun)+"("+str(arg)+")"
    return wrap

def cat_band(banda):
    return "b('"+str(banda)+"')"

# CLEAN sval
DEFAULT_NAMES = {"pi": math.pi,
                 "e": math.e}
DEFAULT_FUNCTIONS = {"max": ExpGen.max,
                     "min": ExpGen.min,
                     "b": cat_band,
                     "exp": cat_fun("exp"),
                     "sqrt": cat_fun("sqrt")}
DEFAULT_OPERATORS = {ast.Add: cat("+"),
                     ast.Sub: cat("-"),
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

if __name__ == "__main__":

    '''
    print "{a}+b".format(a=ExpGen.max("a", 2))

    expr = "maxEE(1, 4)*2"
    print expr.strip()
    for b in ast.parse(expr.strip()).body:
        print dir(b.value.left)
        print dir(b.value.right)
        print b.value.op
    # print ExpGen.parse(expr)
    '''
    expr = "sqrt(2*4)+min(b('B1'), 3)*2*b('B2')"
    expr2 = "1.0-(1.0/(exp((({var}-'mean')*(1/'max'*'a')))+1.0))"
    expr3 = "(3+2)*5"
    #s = SvalEE()
    #print s.eval(expr)
    print ExpGen.parse(expr2)