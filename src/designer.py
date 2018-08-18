# SETUP
# ImageMagick 6.9 https://sourceforge.net/projects/imagemagick/files/im6-exes/ImageMagick-6.9.9-37-Q8-x64-dll.exe/download
# GhostScript 9.23 https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs923/gs923w64.exe

import pandas as pd
import numpy as np
import tweepy
import urllib
import re
from bs4 import BeautifulSoup as bs
from tqdm import tqdm
pd.options.mode.chained_assignment = None 
import arrow
import datetime
from matplotlib import pyplot as plt
import PyPDF2
import io
import sys
import os
import PIL
import random
from PIL import Image
from PIL import ImageDraw 
from PIL import ImageFont 
import textwrap
import math
from parse import humanReadableDate
import cv2
from parse import convert

titleColor = (0,0,0)
authorsColor = (100,100,100)
detailsColor = (50,50,50)
linkColor = (100,100,255)
leftTextMargin = 50
topTextMargin = 50


def faderV(img):
    arr = np.array(img)
    alpha = arr[:, :, 3]
    n = len(alpha)
    alpha[:] = np.interp(np.arange(n), [0, 0.90*n, n], [255, 255, 0])[:,np.newaxis]
    return Image.fromarray(arr, mode='RGBA')



def faderH(img):
    arr = np.array(img.rotate(-90, expand=True))
    alpha = arr[:, :, 3]
    n = len(alpha)
    alpha[:] = np.interp(np.arange(n), [0, 0.95*n, n], [255, 255, 0])[:,np.newaxis]
    return Image.fromarray(arr, mode='RGBA').rotate(90, expand=True)


    
def getPDF(aid):
    return urllib.request.urlretrieve(f"https://arxiv.org/pdf/{aid}", f"../db/pdfs/{aid}.pdf")


def makeText(params, canvas):
    white = Image.new('RGBA', (3020,1000), (255,255,255))
    fontTitle = ImageFont.truetype('../style/fonts/times.ttf', 150)
    fontAuthors = ImageFont.truetype('../style/fonts/times.ttf', 70)
    fontDetails = ImageFont.truetype('../style/fonts/times.ttf', 50)
    
    draw = ImageDraw.Draw(white)
    para = textwrap.wrap(params['title'], width=45)
    current_h, pad = 0, 10
    for i, line in enumerate(para):
        if (i == 2):
            w, h = draw.textsize(" ".join(para[2:]), font=fontTitle)
            draw.text((0, current_h), " ".join(para[2:]), titleColor, font=fontTitle)
            current_h += h + pad
            break
        else:
            w, h = draw.textsize(line, font=fontTitle)
            draw.text((0, current_h), line, titleColor, font=fontTitle)
            current_h += h + pad
        
    para = textwrap.wrap(params['author_all'], width=95)
    current_h += 20
    pad = 5
    for i, line in enumerate(para):
        if (i == 1):
            w, h = draw.textsize(" ".join(para[1:]), font=fontAuthors)
            draw.text((0, current_h), " ".join(para[1:]), authorsColor, font=fontAuthors, )
            current_h += h + pad
            break
        else:
            w, h = draw.textsize(line, font=fontAuthors)
            draw.text((0, current_h), line, authorsColor, font=fontAuthors, )
            current_h += h + pad
        
    current_h += 30

    w, h = draw.textsize(params["ui_submitted"], font=fontDetails)
    draw.text((0, current_h), params["ui_submitted"], detailsColor, font=fontDetails, )
    current_h += h + pad
    w, h = draw.textsize(params["ui_subject"], font=fontDetails)
    draw.text((0, current_h), params["ui_subject"], detailsColor, font=fontDetails, )
    current_h += h + pad
    w, h = draw.textsize(params["ui_comment"], font=fontDetails)
    draw.text((0, current_h), params["ui_comment"], detailsColor, font=fontDetails, )
    current_h += h + pad
    w, h = draw.textsize(params["pdf"], font=fontDetails)
    draw.text((0, current_h), params["pdf"], linkColor, font=fontDetails, )
    current_h += h + pad
    
    white = white.crop((0,0,white.width, current_h))
    white = faderH(white) 
    background = Image.new(white.mode[:-1], white.size, (255,255,255))
    background.paste(white, white.split()[-1])
    return background
    

def makeWordcloud(key, height):
    from wordcloud import WordCloud
    import random

    def grey_color_func(word, font_size, position, orientation, random_state=None,
                    **kwargs):
        o = 120/(font_size*20)
        return "hsl(0, 0%%, %d%%)" % (o + random.randint(20, 30))

    mask = Image.new('RGBA', (876,height), (0,0,0))
    text = convert(f'../db/pdfs/{key}.pdf')
    stopwords = set(map(str.strip, open('./stopwords.txt').readlines()))
    wordcloud = WordCloud(background_color="white", stopwords=stopwords, margin=20, mask=np.array(mask), collocations=True).generate(text)
    return wordcloud.recolor(color_func=grey_color_func, random_state=3)

def makeAbstract(params, canvas):
    white = Image.new('RGBA', (876,1775), (255,255,255))
    font = ImageFont.truetype('../style/fonts/times.ttf', 40)
    
    draw = ImageDraw.Draw(white)
    para = textwrap.TextWrapper(width=50).wrap(params['summary'])

    current_h, pad = 0, 10
    for line in para:
        w, h = draw.textsize(line, font=font)
        draw.text((0, current_h), line, (0,0,0), font=font, )
        current_h += h + pad
    
    if (white.height - current_h) > 200:
        wc = makeWordcloud(params['key'][2:],  white.height - current_h - 20).to_image()
        wc.putalpha(200)
        white.paste(wc, (0,1775 - wc.height), wc)

    bg = Image.open(canvas, 'r') if isinstance(canvas, str) else canvas
    bg.paste(faderV(white), (148,211))
    
    return bg


    
def placeHighlight(page, pagesize, canvas, coord):
    img = Image.open(page, 'r')
    img = img.resize(pagesize, Image.ANTIALIAS)
    white = Image.new('RGBA', img.size, (255,255,255))
    img = img.convert("RGBA")
    white.paste(img, img)
    
    if isinstance(canvas, str):
        bg = Image.open(canvas, 'r')
    else:
        bg = canvas
    bg.paste(white, coord)
    return bg

# source https://www.pyimagesearch.com/2017/06/05/computing-image-colorfulness-with-opencv-and-python/
def imageColorfulness(img):
    # split the image into its respective RGB components
    (B, G, R) = cv2.split(img.astype("float"))
 
    # compute rg = R - G
    rg = np.absolute(R - G)
 
    # compute yb = 0.5 * (R + G) - B
    yb = np.absolute(0.5 * (R + G) - B)
 
    # compute the mean and standard deviation of both `rg` and `yb`
    (rbMean, rbStd) = (np.mean(rg), np.std(rg))
    (ybMean, ybStd) = (np.mean(yb), np.std(yb))
 
    # combine the mean and standard deviations
    stdRoot = np.sqrt((rbStd ** 2) + (ybStd ** 2))
    meanRoot = np.sqrt((rbMean ** 2) + (ybMean ** 2))
 
    # derive the "colorfulness" metric and return it
    return stdRoot + (0.3 * meanRoot)


def getBestPages(aid):
    # Get Images (Temporary)
    directory = f"../db/imgs/{aid}/"
    imgs = os.listdir(directory)
    imgs = list(map(lambda x: directory + x, imgs))
    imgs[1:] = sorted(imgs[1:], key=lambda x: imageColorfulness(cv2.imread(x)), reverse=True)
    return imgs[:4]


def getAllPages(aid):
    # Get Images (Temporary)
    directory = f"../db/imgs/{aid}/"
    imgs = os.listdir(directory)
    imgs.sort()
    imgs = list(map(lambda x: directory + x, imgs))
    return imgs

def makeMinimap(aid, canvas):
    pages = getAllPages(aid)
    imgs = []
    for i in range(len(pages)):
        imgs.append(placeHighlight(pages[i], (309,401), canvas, (3,3)))
    
    total_width = sum([i.width for i in imgs]) + len(imgs)*10
    longimage = Image.new('RGBA', (total_width, imgs[0].height))
    
    offset = 0
    for img in imgs:
        longimage.paste(img, (offset,0))
        offset += 10 + img.width

    return longimage

def makeHighlights(aid, canvas):
    pages = getBestPages(aid)
    coords = [(50,50), (801,50), (1553,50), (2304,50)]
    for i in range(len(pages)):
        canvas = placeHighlight(pages[i], (720, 920), canvas, coords[i])
    return canvas 
      
def assembler(partials):
    canvas = Image.open("../style/png/empty.png", 'r')
    
    # Paste Text
    canvas.paste(partials['text'], (leftTextMargin, topTextMargin))
    
    # Paste Highlights
    yPosition = canvas.height - partials['highlights'].height
    canvas.paste(partials['highlights'], (0, yPosition), partials['highlights'])
    
    # Paste MiniMap
    try:
        mapHeight = canvas.height - partials['highlights'].height - partials['text'].height - 140
        mapWidth = math.floor(partials['minimap'].width / (partials['minimap'].height / mapHeight))
        partials['minimap'] = partials['minimap'].resize((mapWidth, mapHeight), Image.ANTIALIAS)
        yPosition = topTextMargin + partials['text'].height + 60
        canvas.paste(partials['minimap'], (leftTextMargin, yPosition), partials['minimap'])
    except:
        print(f"MiniMap fail -> H:{partials['highlights'].height} + T:{partials['text'].height} = {partials['highlights'].height + partials['text'].height} ~ {canvas.height}")
    
    # Paste Abstract
    xPosition = canvas.width - partials['abstract'].width
    canvas.paste(partials['abstract'], (xPosition, 0), partials['abstract'])
    
    
    return canvas

def checkIntroExists(key):
    return 

def tryDeterminePages(key):
    if os.path.exists(f"../db/imgs/{key[2:]}"):
        return len(os.listdir(f"../db/imgs/{key[2:]}"))
    
def generateIntro(params):
    if os.path.exists(f"../db/intros/{params['key'][2:]}.jpeg"):
        return Image.open(f"../db/intros/{params['key'][2:]}.jpeg")

    partials = {}
    partials['text'] = makeText(params, "../style/png/empty.png")
    partials['abstract'] = makeAbstract(params, "../style/png/abstract.png")
    partials['highlights'] = makeHighlights(params['key'][2:], "../style/png/highlights.png")

    if params['pages'] == '-':
        params['pages'] = tryDeterminePages(params['key'])
    if params['pages'] != '-' and int(params['pages']) > 4: 
        partials['minimap'] = makeMinimap(params['key'][2:], "../style/png/mini.png")
    
    canvas = assembler(partials)
    
    if canvas.mode in ('RGBA', 'LA'):
        background = Image.new(canvas.mode[:-1], canvas.size, (255,255,255))
        return background.paste(canvas, canvas.split()[-1])
    
    return canvas

    

# params = {'author_all': 'Kevis-Kokitsi Maninis, Sergi Caelles, Jordi Pont-Tuset, Luc Van Gool', 'author_main': 'Kevis-Kokitsi Maninis et al.', 'category_ids': 'cs.CV', 'category_primary': 'Computer Vision and Pattern Recognition', 'category_primary_id': 'cs.CV', 'comment': 'CVPR 2018 camera ready. Project webpage and code: http://www.vision.ee.ethz.ch/~cvlsegmentation/dextr/', 'key': 'A:1711.09081', 'keywords': '-', 'pages': 10, 'pdf': 'https://arxiv.org/pdf/1711.09081.pdf', 'published': '2017-11-24T18:54:35Z', 'success': 'nan', 'summary': 'This paper explores the use of extreme points in an object (left-most, right-most, top, bottom pixels) as input to obtain precise object segmentation for images and videos. We do so by adding an extra channel to the image in the input of a convolutional neural network (CNN), which contains a Gaussian centered in each of the extreme points. The CNN learns to transform this information into a segmentation of an object that matches those extreme points. We demonstrate the usefulness of this approach for guided segmentation (grabcut-style), interactive segmentation, video object segmentation, and dense segmentation annotation. We show that we obtain the most precise results to date, also with less user input, in an extensive and varied selection of benchmarks and datasets. All our models and code are publicly available on http://www.vision.ee.ethz.ch/~cvlsegmentation/dextr/.', 'title': 'Deep Extreme Cut: From Extreme Points to Object Segmentation', 'ui_comment': 'Comment: CVPR 2018 camera ready. Project webpage and code: http://www.vision.ee.ethz.ch/~cvlsegmentation/dextr/', 'ui_subject': 'Subject: Computer Vision and Pattern Recognition [cs.CV]', 'ui_submitted': 'Updated in Mar 27, 2018', 'updated': '2018-03-27T11:47:16Z', 'words': '-'}
  
# im = generateIntro(params)
# plt.interactive(False)
# plt.imshow(im)
# plt.show()