import os
os.chdir("D:/George/Projects/PaperTrends/src")


import sys
from twitter import TwitterParser
from arxiv import ArxivAPI
import pandas as pd
from designer import generateIntro
from tqdm import tqdm

class Trend:

    def __init__(self, user='arxivtrends', ignoreposted=False):
        print("Trend initialized")
        self.twitter = TwitterParser(user=user)
        self.ignoreposted = ignoreposted

    def candidates(self, n=10, feed='popular', loadsave=False, top=10, days=2):
        if loadsave:
            self.twitter = self.twitter.loadSaved()
        else:
            self.twitter = self.twitter.loadSaved().parse(keyword="arxiv.org/", regex="\d\d\d\d\.[0-9A-z]*", feed=feed, n=n).save()
        
        # df = self.twitter.aggregated().sort_values('favorited', ascending=False)
        df = self.twitter.filter(favorited=1, retweeted=1).aggregated(favorited=1, retweeted=1, tweets=2).sort_values('retweeted', ascending=False)

        try:
            if not self.ignoreposted:
                posted = self._loadPosted()['key'].astype(str).values
                self.candDF = df[~df['key'].isin(posted)].head(top)
            else:
                self.candDF = df.head(top)
                
        except:
            self.candDF = df.head(top)

        print(self.candDF)

        print(f"> Selected {len(self.candDF)} candidates")
        # print(self.candDF)
        return self

    def _loadPosted(self):
        try:
            self.posted = pd.read_csv("../db/csv/posted.csv")
        except:
            self.posted = pd.DataFrame(columns=['key','posted'])

        return self.posted

    def parse(self):
        print(f"> Fetching keys {self.candDF['key'].values}")
        arxiv = ArxivAPI().fetch(self.candDF['key'].values)
        self.df = pd.DataFrame(arxiv)

        return self

    def generate(self):
        print(f"> Generating intros")
        pbar = tqdm(self.df.to_dict('records'))
        for record in pbar:
            pbar.set_description(f"Intro image {record['key']}")
            try:
                image = generateIntro(record)
                image.save(f"../db/intros/{record['key'][2:]}.jpeg", quality=95)
            except FileNotFoundError:
                print("Intro generation Failed", record['key'], f"{sys.exc_info()[0]} ~ {str(e)}")
                
            except Exception as e:
                raise
                print("Intro generation Failed", record['key'], f"{sys.exc_info()[0]} ~ {str(e)}")
                self.df = self.df[~self.df['key'].isin([record['key']])]

        return self

    def getDF(self):
        return self.df

    def post(self):
        print(f"> Posting tweets")
        try:
            posted = pd.read_csv("../db/csv/posted.csv")
        except:
            posted = pd.DataFrame(columns=['key','posted'])
        e = pd.read_csv('../db/csv/emojis.csv', encoding='utf-8')
        pbar = tqdm(self.df.to_dict('records'))
        try:

            for rec in pbar:
                tweet = self.composeTweet(rec,e)
                print(tweet)
                self.twitter.api.update_with_media(f"../db/intros/{rec['key'][2:]}.jpeg", tweet)
                if not self.ignoreposted:
                    posted = posted.append({
                        'key': str(rec['key']),
                        'posted': pd.datetime.now()
                    }, ignore_index=True)
        except Exception as e:
            print(str(e))
            print(rec['keywords'])

        if not self.ignoreposted:
            posted.to_csv("../db/csv/posted.csv", index=False)

        return self

    def composeTweet(self, rec, e):
        emoji = e[e['id'] == rec['category_primary_id']]['emoji'].values[0]
        tweet = f"{emoji} {rec['title']}\n"
        tweet += f"✍️ {rec['author_main']}\n"
        tweet += f"🔗 {rec['pdf']}\n\n"
        try:
            tweet += f"🔊 Tweeted by {self.candDF[self.candDF['key'] == rec['key']].head(1)['users'].values[0]} et al.\n"
        except:
            print("no users")
        keywords = '#'+rec['category_primary'].replace('-','').replace(' ','') 
        rec['keywords'] = rec['keywords'].replace('#boringformattinginformation','')
        keywords += ' ' + ' '.join(list(map(lambda x: '#'+x, rec['keywords'].replace('.','').replace(' ','').replace('-','').split(',')))) if rec['keywords'] != '-' and rec['keywords'] != '' else ''
        keywords += ' ' + ' '.join(list(map(lambda x: '#'+x, rec['category_ids'].replace('.','').replace(' ','').replace('-','').split(','))))
        tweet += f"{keywords}"
        return tweet

    def postCustom(self, keys):
        try:
            posted = pd.read_csv("../db/csv/posted.csv")
        except:
            posted = pd.DataFrame(columns=['key','posted'])
        records = pd.DataFrame(ArxivAPI().fetch(keys)).to_dict('records')
        e = pd.read_csv('../db/csv/emojis.csv', encoding='utf-8')
        for rec in records:
            image = generateIntro(rec)
            image.save(f"../db/intros/{rec['key']}.jpeg", quality=95)
            tweet = self.composeTweet(rec, e)
            TwitterParser().api.update_with_media(f"../db/intros/{rec['key']}.jpeg", tweet)
            posted = posted.append({
                    'key': str(rec['key']),
                    'posted': pd.datetime.now()
                }, ignore_index=True)
            print(tweet)
        posted.to_csv("../db/csv/posted.csv", index=False)
        

    def loadPostedCandidates(self):
        self.twitter = self.twitter.loadSaved()
        df = self.twitter.filter(favorited=1, retweeted=1, days=999).getDF()
        posted = self._loadPosted()['key'].astype(str).values
        self.candDF = df[df['key'].isin(posted)]
        return self

    def deleteEverything(self):
        import tweepy
        for status in tweepy.Cursor(self.twitter.api.user_timeline).items():
            try:
                self.twitter.api.destroy_status(status.id)
                print("Deleted:", status.id)
            except:
                print("Failed to delete:", status.id)
                raise
        

### Test
# t = Trend(user='anbanige', ignoreposted=True).candidates(n=100, feed='popular', loadsave=True, top=5, days=15).parse().generate()
# t = Trend(user='arxivtrends', ignoreposted=False).candidates(n=100, feed='popular', loadsave=True, top=1, days=15).parse().generate().post()
# t = Trend().candidates(n=500, feed='mixed', loadsave=False, top=5, days=15).parse().generate().post()
# Trend(user='anbanige').postCustom(['A:1606.03657','A:1508.06576'])
# Trend(user='anbanige').deleteEverything()

# t = Trend().loadPostedCandidates().parse().generate().post()


