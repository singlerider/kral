# -*- coding: utf-8 -*-
from eventlet.greenthread import sleep
from eventlet.green import urllib2
import urllib
from collections import defaultdict
from kral.utils import fetch_json
from kral import config

#TODO: look into using the start-index and max-results parameters

def stream(queries, queue, kral_start_time):

    print('-'*50)
    print str(config)

    mode = config.YOUTUBE['mode'] or 'most_popular' .get('Youtube', 'mode', 'most_popular')

    api_url = "http://gdata.youtube.com/feeds/api/standardfeeds/%s?" % mode 
    
    prev_ids = defaultdict(list)

    while True:
        for query in queries:

            p = {
                'q': query,
                'orderby': config.YOUTUBE['orderby'] or 'published',
                'max-results': config.YOUTUBE['maxresults'] or 25,
                'v': 2, 
                'alt': 'jsonc',
                'format': 5,
            }    

            #time is only supported in these standard video feeds
            if mode in ['top_rated', 'top_favorites', 'most_viewed', 
                    'most_popular', 'most_discussed', 'most_responded',]:
                p['time'] = config.YOUTUBE['time'] or 'today'

            url  =  api_url + urllib.urlencode(p)
            
            request = urllib2.Request(url)
    
            request.add_header('User-agent', config.USER_AGENT)

            response = fetch_json(request)
            
            if not response:
                sleep(5)
                break

            if 'data' in response and 'items' in response['data']:
                
                entries = response['data']['items']
                
                for entry in entries:
                    #['uploaded',
                    #'category', 
                    #'updated',
                    #'rating',
                    #'description',
                    #'title',
                    #'tags',
                    #'thumbnail',
                    #'content', 
                    #'player',
                    #'accessControl',
                    #'uploader',
                    #'ratingCount',
                    #'duration',
                    #'aspectRatio', 
                    #'likeCount',
                    #'favoriteCount',
                    #'id', 
                    #'viewCount']
                    
                    entry_id =  entry['id']
                    
                    uploader = entry['uploader']

                    profile_url = "http://youtube.com/" + uploader

                    if entry_id not in prev_ids[query]: #if we've already seen this id skip it

                        post = {
                            "service"     : "youtube",
                            "id"          : entry_id, 
                            "query"       : query,
                            "date"        : entry['uploaded'],
                            "user"        : {
                                                "name"    : uploader,
                                                "profile" : profile_url,
                                            },
                            "source"      : entry['player']['default'],
                            "text"        : entry['title'],
                            "description" : entry.get('description', ''),
                            "category"    : entry['category'],
                            "keywords"    : entry.get('tags', ''),
                            "duration"    : entry['duration'], 
                            'favorites'   : entry.get('favoriteCount', 0),
                            'views'       : entry.get('viewCount', 0),
                            'likes'       : entry.get('likeCount', 0),
                        }
                        #ratingCount – The total number of voters who have rated the video using either rating system.
                        #The number of voters who disliked the video can be calculated by subtracting the likeCount from the ratingCount.
                        post['dislikes'] = int(entry.get('ratingCount', 0)) - int(post['likes'])
                        
                        prev_ids[query].insert(0, entry_id) #add the entry ids to previous ids for query

                        queue.put(post)
                
            #use 50 item buffer for dupes
            #TODO: look into deque
            prev_ids[query] = prev_ids[query][:50] 
            
            sleep(15)
