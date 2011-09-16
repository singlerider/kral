import eventlet
import base64
import time
import datetime
import re
import simplejson as json
from eventlet.green import urllib2
from utils import fetch_json

#Global settings. Import and customize.
settings = {
    'TIME_FORMAT' : "%Y-%m-%dT%H:%M:%S+0000",
    'BUZZ_API_KEY' : '',
    'FLICKR_API_KEY' : '',
    'FACEBOOK_API_KEY' : '',
    'TWITTER_USER' : '',
    'TWITTER_PASS' : ''
}

def facebook(queries, queue, settings):
    while True:
        for query in queries:
            time.sleep(1)
            url = "https://graph.facebook.com/search?q=%s&type=post&limit=25&access_token=%s"
            url = url % (query,settings['FACEBOOK_API_KEY'])
            data = fetch_json('facebook',url)
            if data:
                items = data['data']
                for item in items:
                    if 'message' in item:
                        post = {
                            "service" : 'facebook',
                            "query": query,
                            "user" : {
                                "name": item['from'].get('name'),
                                "id": item['from']['id'],
                            },
                            "links" : [],
                            "id" : item['id'],
                            "text" : item['message'],
                            "date": str(datetime.datetime.strptime(item['created_time'], settings['TIME_FORMAT'])),
                        }
                        url_regex = re.compile('(?:http|https|ftp):\/\/[\w\-_]+(?:\.[\w\-_]+)+(?:[\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?')
                        for url in url_regex.findall(item['message']):
                            post['links'].append({ 'href' : url })
                        post['user']['avatar'] = "http://graph.facebook.com/%s/picture" % item['from']['id']
                        if 'to' in item:
                            post['to_users'] = item['to']['data']
                        if 'likes' in item:
                            post['likes'] = item['likes']['count']
                        queue.put(post)

def twitter(queries, queue, settings):
    url = 'http://stream.twitter.com/1/statuses/filter.json'
    query_post = str("track="+",".join([q for q in queries]))
    httprequest = urllib2.Request(url,query_post)
    auth = base64.b64encode('%s:%s' % (settings['TWITTER_USER'], settings['TWITTER_PASS']))
    httprequest.add_header('Authorization', "basic %s" % auth)
    for item in urllib2.urlopen(httprequest):
        item = json.loads(item)
        post = {
            'service' : 'twitter',
            'user' : {
                'id' : item['user']['id_str'],
                'utc' : item['user']['utc_offset'],
                'name' : item['user']['screen_name'],
                'description' : item['user']['description'],
                'location' : item['user']['location'],
                'avatar' : item['user']['profile_image_url'],
                'subscribers': item['user']['followers_count'],
                'subscriptions': item['user']['friends_count'],
                'website': item['user']['url'],
                'language' : item['user']['lang'],
            },
            'links' : [],
            'id' : item['id'],
            'application': item['source'],
            #'date' : str(datetime.datetime.strptime(item['created_at'], settings['TIME_FORMAT'])),
            'text' : item['text'],
            'geo' : item['coordinates'],
        }
        for url in item['entities']['urls']:
            post['links'].append({ 'href' : url.get('url') })
        queue.put(post)

def stream(queries, services, settings=settings):
    """
    Yields latest public postings from major social networks for givenquery or
    queries.

    Keyword arguments:
    queries  -- a single query (string) or multiple queries (list)
    services -- a single service (string) or multiple services (list)

    """
    service_functions = {
        'facebook': facebook,
        'twitter': twitter
    }

    if type(services) is str:
        services = [services]
    if type(queries) is str:
        queries = [queries]

    queue = eventlet.Queue()

    for service in service_functions:
        if service in services:
            eventlet.spawn(service_functions[service], queries, queue, settings)

    while True:
        yield queue.get()


if __name__ == '__main__':
    count = 0
    for item in stream(['android','bitcoin'],['facebook','twitter']):
        count += 1
        print u"{0:7d} | {1:8s} | {2:18s} | {3:140s}".format(count,item['service'], item['user']['name'], item['text'].replace('\n',''))
