# !/usr/bin/env python
# -*- coding: utf-8 -*-
''' DEPRECATED. Replaced by geetools '''

# computo de bits para mascaras a partir de la banda QA de LEDAPS
def getQABits(image, start, end, newName):
    # Compute the bits we need to extract
    pattern = 0

    for i in range(start, end + 1):
        pattern += 2**i

    # Return a single band image of the extracted QA bits, giving the band
    # a new name.

    return image.select([0], [newName]).bitwiseAnd(pattern).rightShift(start)

# MODIS
def modis(img):
    cmask = img.select("state_1km")
    cloud = getQABits(cmask, 1, 1, "cloud")
    mix = getQABits(cmask, 0, 0, "mix")
    shadow = getQABits(cmask, 2, 2, "shadow")
    cloud2 = getQABits(cmask, 10, 10, "cloud2")
    snow = getQABits(cmask, 11, 11, "snow")

    mask = cloud.Or(mix).Or(shadow).Or(cloud2).Or(snow)

    return img.updateMask(mask.Not())


# SENTINEL
def sentinel(image):
    nubes = image.select("QA60")
    opaque = getQABits(nubes, 10, 10, "opaque")
    cirrus = getQABits(nubes, 11, 11, "cirrus")
    mask = opaque.Or(cirrus)
    result = image.updateMask(mask.Not())
    return result


# LEDAPS
def ledaps(image):
    cmask = image.select('QA')

    valid_data_mask = getQABits(cmask, 1, 1, 'valid_data')
    cloud_mask = getQABits(cmask, 2, 2, 'cloud')
    snow_mask = getQABits(cmask, 4, 4, 'snow')

    good_pix = cloud_mask.eq(0).And(valid_data_mask.eq(0)).And(snow_mask.eq(0))
    result = image.updateMask(good_pix)

    return result

# FMASK
def fmask(image):
    imgFmask = image.select("fmask")
    shadow = imgFmask.eq(3)
    snow = imgFmask.eq(4)
    cloud = imgFmask.eq(5)

    mask = shadow.Or(snow).Or(cloud)

    imgMask = image.updateMask(mask.Not())
    return imgMask


def cfmask(image):
    imgFmask = image.select("cfmask")
    shadow = imgFmask.eq(3)
    snow = imgFmask.eq(4)
    cloud = imgFmask.eq(5)

    mask = shadow.Or(snow).Or(cloud)

    imgMask = image.updateMask(mask.Not())
    return imgMask

def usgs(image):
    image = cfmask(image)
    cloud = image.select("sr_cloud_qa").neq(255)
    shad = image.select("sr_cloud_shadow_qa").neq(255)
    return image.updateMask(cloud).updateMask(shad)
