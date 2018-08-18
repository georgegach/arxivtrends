import os
os.chdir("D:/George/Projects/PaperTrends/src")
import tweepy
from tqdm import tqdm
import pandas as pd
import sys 

disableTQDM = False
class TwitterParser():

    def __init__(self, user='arxivtrends'):
        print("> Twitter Parser initialized")
        keys = self._readAPIKeys("env.json", user)
        auth = tweepy.OAuthHandler(keys['consumer_key'], keys['consumer_secret'])
        auth.set_access_token(keys['access_token'], keys['access_token_secret'])
        self.api = tweepy.API(auth)
        self.df = None
        self.debug = None

    def parse(self, keyword="arxiv.org/", regex="\d\d\d\d\.[0-9A-z]*", feed='popular', n=1000):
        print(f"> Parsing [{keyword}] keyword from [{feed}] feed for [{n}] tweets.")
        
        public_tweets = tweepy.Cursor(self.api.search, q=keyword, result_type=feed, tweet_mode="extended").items(n)
        self.tweets = []
        total = 0
        pbar = tqdm(public_tweets, disable=disableTQDM)
        try:
            for tweet in pbar:
                pbar.set_description(f"Parsing tweet [❤️ :{tweet.favorite_count} ↪️ :{tweet.retweet_count}]")
                total += 1
                if tweet.favorite_count > 0 and tweet.retweet_count > 0:
                    self.tweets.append(tweet)
                
                if 'retweeted_status' in tweet.__dict__.keys():
                    self.tweets.append(tweet.retweeted_status)

        except Exception as e:
            print(f"{sys.exc_info()[0]} ~ {str(e)}")

        print(f">> Total tweets: {total}. Filtered tweets (❤️ >0 or ↪️ >0): {len(self.tweets)}")
        print(f"> Generating dataframe from raw tweets for regex scheme /{regex}/")
        import re
        import urllib

        dfList = []
        pbar = tqdm(self.tweets, disable=disableTQDM)
        for t in pbar:
            try:
                if t.entities['urls'] != []:
                    url = urllib.request.urlopen(t.entities['urls'][0]['url']).geturl()
                else:
                    url = urllib.request.urlopen(t.retweeted_status.entities['urls'][0]['url']).geturl()
                
                key = re.findall(re.compile(regex), url)
                if key != []:
                    key = key[0]
                else:
                    continue
                pbar.set_description(f"Key found: [{key}]")
            except urllib.error.HTTPError as e:
                print(f"https://twitter.com/{t.user.screen_name}/status/{t.id} {sys.exc_info()[0]} ~ {str(e)}")
                continue
            except Exception as e:
                print(str(e))
                print(f"https://twitter.com/{t.user.screen_name}/status/{t.id} {sys.exc_info()[0]}")
                self.debug = t
                pbar.set_description(f"Key was not found. https://twitter.com/{t.user.screen_name}/status/{t.id}")
                continue
            key = key.split('v')[0]
            dfList.append({
                'key': 'A:'+key,
                'id':t.id,
                'user': t.user.screen_name,
                'favorited': t.favorite_count,
                'retweeted': t.retweet_count,
                'created_at': t.created_at,
                'time_delta': pd.datetime.now()-pd.to_datetime(t.created_at),
                'url': url,
                'text': self._cleanText(t.full_text),
            })

        if self.df is not None:
            oldlen = len(self.df)
            newDF = pd.DataFrame(dfList, columns=['key', 'id', 'user', 'favorited', 'retweeted', 'created_at', 'url', 'text'])

            oldIds = self.df['id'].values
            newIds = newDF['id'].values

            remainIds = list(set(oldIds) - set(newIds))
            self.df = pd.concat([self.df[self.df['id'].isin(remainIds)], newDF])
            self.df = self.df.sort_values("favorited", ascending=False)
            print(f"> Dataframe updated ({oldlen} + {len(newDF)}) -> ({len(self.df)})")
        else:
            self.df = pd.DataFrame(dfList, columns=['key', 'id', 'user', 'favorited', 'retweeted', 'created_at', 'url', 'text'])
            self.df = self.df.sort_values("favorited", ascending=False)
        return self



    def loadSaved(self, path='../db/csv/', filename=None):
        if filename != None:
            self.df = pd.read_csv(path+filename, encoding='utf-8')
        else:
            from stat import S_ISREG, ST_CTIME, ST_MODE
            import os, sys, time
            entries = (os.path.join(path, fn) for fn in os.listdir(path))
            entries = ((os.stat(path), path) for path in entries)
            entries = [{'ctime': stat[ST_CTIME], 'path': path} for stat, path in entries if S_ISREG(stat[ST_MODE])]
            entries.sort(key = lambda x: -x['ctime'])
            entries = [x for x in entries if 'arxiv' in x['path'].split('/')[-1]]
            self.df = pd.read_csv(entries[0]['path'], encoding='utf-8')
        
        return self

    def aggregated(self, favorited=1, retweeted=1, tweets=2):
        def bestTweeters(key, df):
            return ', '.join(['@'+u for u in df[df['key'] == key].sort_values('favorited', ascending=False)[['favorited', 'retweeted', 'user']].head()['user'].unique()])
    
        self.dfagg = self.df.groupby('key').agg({'id':'count','favorited':'sum','retweeted':'sum'}).rename(columns={'id': 'tweets'}).sort_values('tweets', ascending=False)
        self.dfagg['key'] = self.dfagg.index
        self.dfagg = pd.DataFrame(self.dfagg.to_dict('records'))
        self.dfagg['users'] = self.dfagg.apply(lambda x: bestTweeters(x['key'], self.df), axis=1)

        self.dfagg = self.dfagg[self.dfagg['favorited'] >= favorited]
        self.dfagg = self.dfagg[self.dfagg['retweeted'] >= retweeted]
        self.dfagg = self.dfagg[self.dfagg['tweets'] >= tweets]

        return self.dfagg

    def filter(self, favorited=0, retweeted=0, days=365):
        before = len(self.df)

        # [self.df['timedelta'].dt.days < days]
        
        # filter by favorites and retweeted
        self.df = self.df[self.df['favorited'] > favorited]
        self.df = self.df[self.df['retweeted'] > retweeted]
        

        after = len(self.df)
        print(f"> Remaining filtered tweets: {int((after/before)*100)}% [{after}/{before}]")
        # print(self.df)
        return self


    def save(self, path='../db/csv/', key='arxiv'):
        import datetime
        dateString = str(datetime.datetime.now().date()).replace('-','')
        filename = f"{key}-{dateString}.csv"
        self.df.to_csv(path + filename, encoding='utf-8', index=False)
        print(f"> Dataframe saved in .csv file: {path+filename}")
        return self
    
    def getDF(self):
        return self.df

    def _readAPIKeys(self, path, user):
        import json
        with open(path) as env:
            e = json.load(env)
            return e['keys']['twitter'][user]
    
    def _cleanText(self, text):
        return ' '.join(text.replace('\n',' ').replace('\r','').split())


### Test
# t = TwitterParser().loadSaved().parse(keyword='arxiv.org/', regex='\d\d\d\d.[0-9A-z]*', feed='popular', n=100).save()
# print(t.getDF())