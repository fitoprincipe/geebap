# -*- coding: utf-8 -*-
""" Util functions """


def get_init_params(obj):
    init_params = obj.__init__.__code__.co_varnames
    obj_params = obj.__dict__.items()
    return {param: value for param, value in obj_params if param in init_params}


def object_init(obj):
    init_params = get_init_params(obj)
    return '{}(**{})'.format(obj.__class__.__name__, init_params)


def serialize(obj, name=None, result=None):
    """ Serialize an object to a dict """
    if result is None:
        result = {}

    def make_name(obj, name=None):
        objname = obj.__class__.__name__
        if name is None:
            # name = objname
            return '({})'.format(objname)
        return '{} ({})'.format(name, objname)

    name = make_name(obj, name)

    try:
        # If it is an object, it has a __dict__
        obj_attr = obj.__dict__
    except AttributeError:
        # If it's NOT an object
        if isinstance(obj, (tuple, list)):
            newlist = []
            for element in obj:
                newlist.append(serialize(element))
            result[name] = newlist
        elif isinstance(obj, (dict,)):
            newdict = {}
            for key, element in obj.items():
                newdict[key] = serialize(element)
            result[name] = newdict
        else:
            result[name] = obj
    else:
        # If it IS an object
        attrs = {}
        result[name] = attrs
        for attr_name, attr_value in obj_attr.items():
            serialize(attr_value, attr_name, attrs)

    return result
