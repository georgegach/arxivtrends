import os
os.chdir("D:/George/Projects/PaperTrends/src")
import urllib
import re
from bs4 import BeautifulSoup as bs
from tqdm import tqdm
import sys
import os
from etc import category_ids
import PyPDF2
import datetime 
import pandas as pd

disableTQDM = False

class ArxivAPI:

    def __init__(self):
        print("> Arxiv API initialized")
        self.adb = pd.read_csv("../db/csv/adb.csv", encoding='utf-8')
        

    def fetch(self, keys):
        self._downloadPDFs(keys)
        self._generateImages(keys)
        parsed = self._parse(keys)

        return parsed

    def _parse(self, keys):
        entries = self._entries(keys)
        results = []
        pbar = tqdm(entries, disable=disableTQDM)
        for entry in pbar:
            try:
                pbar.set_description(f"Parsing entry")
                results.append(self._parsedEntry(entry))
            except:
                pbar.set_description(f"Error ~ [{sys.exc_info()[0]}]")
                raise
            
        self._mergeWithADB(results)
        return results

    def _mergeWithADB(self, results):
        newDF = pd.DataFrame(results)
        if newDF.empty:
            return
        oldIds = self.adb['key'].values
        newIds = newDF['key'].values

        remainIds = list(set(oldIds) - set(newIds))
        self.adb = pd.concat([self.adb[self.adb['key'].isin(remainIds)], newDF])
        self.adb.to_csv("../db/csv/adb.csv", index=False, encoding='utf-8')

    def _entries(self, keys):
        url = f"http://export.arxiv.org/api/query?id_list={','.join([key[2:] for key in keys])}&max_results={len(keys)}"
        print(url)
        html = urllib.request.urlopen(url).read()
        soup = bs(html, "lxml")
        return soup.findAll('entry')

    def _parsedEntry(self, entry):

        p = {}
        p['key'] = 'A:' + self._cleanText(entry.select_one('id').text.split('/')[-1].split('v')[0])
        
        p['updated'] = self._cleanText(entry.select_one('updated').text)
        
        if self.adb['key'].isin([p['key']]).any():
            if self.adb[self.adb['key'].isin([p['key']])]['updated'].any() == p['updated']:
                recs = self.adb[self.adb['key'].isin([p['key']])]
                return recs.to_dict('records')[0]


        p['author_all'] = ", ".join([self._cleanText(a.text) for a in entry.select("author")])
        p['author_main'] = p['author_all'].split(',')[0] + ' et al.' if len(p['author_all'].split(',')) > 2 else p['author_all']

        p['title'] = self._cleanText(entry.select_one('title').text)
        p['summary'] = self._cleanText(entry.select_one('summary').text)
        
        p['category_ids'] = ', '.join([c['term'] for c in entry.findAll('category')])
        p['category_primary_id'] = entry.find('arxiv:primary_category')['term']
        p['category_primary'] = category_ids[p['category_primary_id']]

        p['published'] = self._cleanText(entry.select_one('published').text)
        p['comment'] = self._cleanText(entry.find('arxiv:comment').text) if entry.find('arxiv:comment') is not None else '-'


        with open(f"../db/pdfs/{p['key'][2:]}.pdf","rb") as file:
            try:
                pdf = PyPDF2.PdfFileReader(file)
                p['pages'] = pdf.numPages
                p['keywords'] = pdf.documentInfo['/Keywords'] if '/Keywords' in pdf.documentInfo and pdf.documentInfo['/Keywords'] != '' else '-'
                p['words'] = '-'
            except Exception as e:
                print(f" PError [{p['key']}]: {sys.exc_info()[0]} {str(e)}")
                p['pages'] = '-'
                p['keywords'] = '-'
                p['words'] = '-'

        p['ui_comment'] = f"Comment: {p['comment']}" if p['comment'] != '-' else f"Comment: [ {p['pages']} pages. ]" if p['pages'] != '!' else ''
        p['ui_subject'] = f"Subject: {p['category_primary']} [{p['category_primary_id']}]"
        p['ui_submitted'] = f"Published {self._humanReadableDate(p['published'])}" if p['published'] == p['updated'] else f"Updated {self._humanReadableDate(p['updated'])}"
        p['pdf'] = f"https://arxiv.org/pdf/{p['key'][2:]}.pdf"  
        return p

    def _downloadPDFs(self, keys):
        print(f"> Downloading PDFs")
        pbar = tqdm(keys, disable=disableTQDM)

        for key in pbar:
            key = key[2:]
            try:
                pbar.set_description(f"Downloading PDF for [{key}]")
                if not os.path.exists(f"../db/pdfs/{key}.pdf"):
                    urllib.request.urlretrieve(f"https://arxiv.org/pdf/{key}.pdf", f"../db/pdfs/{key}.pdf")
                
            except urllib.error.HTTPError:
                print(f" 404 Error: https://arxiv.org/pdf/{key}.pdf")
            except Exception as e:
                pbar.set_description(f" Error [{key}] ~ [{sys.exc_info()[0]}]")
                print(f" DWError [{key}]: {sys.exc_info()[0]} {str(e)}")
                raise
        
    def _generateImages(self, keys):
        print(f"> Generating images")
        
        pbar = tqdm(keys, disable=disableTQDM)
        for key in pbar:
            key = key[2:]
            try:
                if os.path.exists(f"../db/pdfs/{key}.pdf"):
                    if not os.path.exists(f"../db/imgs/{key}"):
                        os.mkdir(f"../db/imgs/{key}")

                if not os.path.exists(f"../db/imgs/{key}/page-0.png"):
                    # from wand.image import Image
                    # with Image(filename=f"../db/pdfs/{key}.pdf", resolution=100) as img:
                    #     with img.convert('png') as converted:
                    #         converted.save(filename=f'../db/imgs/{key}/page.png')

                    from pdf2image import convert_from_path
                    images = convert_from_path(f'../db/pdfs/{key}.pdf')
                    for i, im in enumerate(images):
                        im.save(f"../db/imgs/{key}/page-{i}.png")

            except Exception as e:
                pbar.set_description(f" GENError [{key}] ~ [{sys.exc_info()[0]}]")
                print(f" GENError [{key}]: {sys.exc_info()[0]} {str(e)}")
                raise
    
    def _cleanText(self, text):
        return ' '.join(text.replace('\n',' ').replace('\r','').split())

    def _humanReadableDate(self, date):
        date = pd.to_datetime(date)
        delta = (datetime.datetime.now() - date).days
        if delta == 0:
            return "today"
        if delta == 1:
            return "yesterday"
        if delta < 30:
            return f"{delta} days ago in {date.strftime('%b %d, %Y')}"
        else:
            return f"in {date.strftime('%b %d, %Y')}"

    


### Test
# print(ArxivAPI().fetch(['A:1805.08671','A:1802.07228']))
