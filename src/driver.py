import os
os.chdir("D:/George/Projects/PaperTrends/src")
from trends import Trend
t = Trend(user='arxivtrends', ignoreposted=False).candidates(n=500, feed='mixed', loadsave=False, top=0, days=15).parse().generate().post()
t = Trend(user='arxivtrends', ignoreposted=False).candidates(n=100, feed='popular', loadsave=False, top=1 ,days=15).parse().generate().post()
