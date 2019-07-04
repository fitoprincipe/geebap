# -*- coding: utf-8 -*-
""" Tools to use in IPython """

import ee
from geetools import tools
from . import date, functions


def information():
    pass


def info2map(map):
    """ Add an information Tab to a map displayed with `geetools.ipymap`
    module

    :param map: the Map where the tab will be added
    :type map: geetools.ipymap.Map
    :return:
    """
    try:
        from ipywidgets import Accordion
    except:
        print('Cannot use ipytools without ipywidgets installed\n'
              'ipywidgets.readthedocs.io')

    map.addTab('BAP Inspector', info_handler, Accordion())


def info_handler(**kwargs):
    """ Handler for the Bap Inspector Tab of the Map

    :param change:
    :return:
    """
    try:
        from ipywidgets import HTML
    except:
        print('Cannot use ipytools without ipywidgets installed\n'
              'ipywidgets.readthedocs.io')

    themap = kwargs['map']
    widget = kwargs['widget']
    # Get click coordinates
    coords = kwargs['coordinates']

    event = kwargs['type'] # event type
    if event == 'click':  # If the user clicked
        # create a point where the user clicked
        point = ee.Geometry.Point(coords)

        # First Accordion row text (name)
        first = 'Point {} at {} zoom'.format(coords, themap.zoom)

        # Reset list of widgets and names
        namelist = [first]
        wids4acc = [HTML('')] # first row has no content

        length = len(themap.EELayers.keys())
        i = 1

        for name, obj in themap.EELayers.items(): # for every added layer
            # Clear children // Loading
            widget.children = [HTML('wait a second please..')]
            widget.set_title(0, 'Click on {}. Loading {} of {}'.format(coords, i, length))
            i += 1

            # IMAGES
            if obj['type'] == 'Image':
                # Get the image's values
                image = obj['object']
                properties = image.propertyNames().getInfo()

                if 'BAP_version' in properties:  # Check if it's a BAP composite
                    try:
                        values = tools.image.getValue(image, point, 10, 'client')
                        values = tools.dictionary.sort(values)
                        col_id = int(values['col_id'])
                        thedate = int(values['date'])
                        collection = functions.get_id_col(col_id)
                        realdate = date.Date.get(thedate).format().getInfo()

                        # Get properties of the composite
                        inidate = int(image.get('ini_date').getInfo())
                        inidate = date.Date.get(inidate).format().getInfo()
                        enddate = int(image.get('end_date').getInfo())
                        enddate = date.Date.get(enddate).format().getInfo()

                        # Create the content
                        img_html = '''
                            <h3>General Properties</h3>
                            <b>Season starts at:</b> {ini}</br>
                            <b>Season ends at:</b> {end}</br>
                            <h3>Information at point</h3>
                            <b>Collection:</b> {colid} ({col})</br>
                            <b>Date:</b> {thedate} ({date})'''.format(ini=inidate,
                            end=enddate, col=collection, date=realdate, p=coords,
                            thedate=thedate, colid=col_id)

                        wid = HTML(img_html)
                        # append widget to list of widgets
                        wids4acc.append(wid)
                        namelist.append(name)
                    except Exception as e:
                        widget = HTML(str(e).replace('<','{').replace('>','}'))
                        text = 'ERROR in layer {}'.format(name)
                        wids4acc.append(widget)
                        namelist.append(text)
                else:
                    continue
            # GEOMETRIES
            elif obj['type'] == 'Geometry':
                continue

        # BAP Widget
        # bapwid = m.childrenDict['BAP Inspector']
        widget.children = wids4acc

        for i, n in enumerate(namelist):
            widget.set_title(i, n)