# -*- coding: utf-8 -*-
""" Util functions """


def serialize(obj, name=None, result=None):
    """ Serialize an object to a dict """
    if result is None:
        result = {}

    objname = obj.__class__.__name__
    if name is None:
        name = objname

    name = '{} ({})'.format(name, objname)

    attrs = {}
    result[name] = attrs
    for k, v in obj.__dict__.items():
        try:
            d = v.__dict__
        except AttributeError:
            attr_name = '{} ({})'.format(k, v.__class__.__name__)
            attrs[attr_name] = v
            continue
        else:
            serialize(v, k, attrs)
    return result
