"""
e621 Search Plugin by ararouge
usage:
.e621 [tags]
"""

from core import hook
from random import shuffle
import asyncio
import requests

furry_cache = []
lastsearch = ''
headers = {'User-Agent':'paprika/1.0'}

def refresh_cache(inp):
  global furry_cache
  global headers 
  furry_cache = []
  search = inp.replace(' ','%20').replace('explicit','rating:explicit').replace('nsfw','rating:explicit').replace('safe','rating:safe').replace('sfw','rating:safe')
  if inp == '':
    r = requests.get('http://e621.net/posts.json?limit=20', headers=headers)
  else:
    r = requests.get(f'http://e621.net/posts.json?limit=20&tags={search}', headers=headers)
  posts = r.json()["posts"]
      for i in range(len(posts)):
        post = posts[i]
        id = post.id.get_text()
        score = post.score.total.get_text()
        url = post.file.url
        rating = post.rating
        tags = post.tags.general.join(", ")
        furry_cache.append((id, score, url, rating))
  random.shuffle(furry_cache)
  return

@hook.hook('command', ['furry', 'e621'])
async def furry(client, data):
  global lastsearch
  global furry_cache
  inp = data.message.lower()
  output = ''
  if not(inp in lastsearch) or len(furry_cache) < 2: refresh_cache(inp)
  lastsearch = inp
  if len(furry_cache) == 0: output = "No Results"
  else:
    id, score, url, rating = furry_cache.pop()
    if rating == 'e':
      rating = "\x02\x034NSFW\x03\x02"
    elif rating == 'q':
      rating = "\x02Questionable\x02"
    elif rating == 's':
      rating = "\x02\x033Safe\x03\x02"
    output = f'\x02[{id}]\x02 Score: \x02{score}\x02 - Rating: {rating} - {url}'
  asyncio.create_task(client.message(data.target, output))
