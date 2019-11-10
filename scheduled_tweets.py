# !/usr/bin/env python3
import time
from io import BytesIO
import os
import requests
from airtable import Airtable
from documentcloud import DocumentCloud
from twython import Twython

t0 = time.time()
dc = DocumentCloud(
    os.environ['DOCUMENT_CLOUD_USERNAME'], os.environ['DOCUMENT_CLOUD_PW'])
tw = Twython(os.environ['TWITTER_APP_KEY'], os.environ['TWITTER_APP_SECRET'],
             os.environ['TWITTER_OAUTH_TOKEN'], os.environ['TWITTER_OAUTH_TOKEN_SECRET'])
airtab = Airtable(os.environ['botfeldman89_db'],
                  'scheduled_tweets', os.environ['AIRTABLE_API_KEY'])


def send_next(data):
    results = airtab.get_all(view='not yet tweeted')
    if results:
        record = results[0]
        tweet_dict = {}
        tweet_dict['status'] = record['fields']['msg']
        if record['fields']['re'] == "clippings":
            # Upload images of first four pages
            media_ids = []
            obj = dc.documents.get(record['fields']['dc_id'])
            image_list = obj.normal_image_url_list[:4]
            for image in image_list:
                res = requests.get(image)
                res.raise_for_status()
                uploadable = BytesIO(res.content)
                response = tw.upload_media(media=uploadable)
                media_ids.append(response['media_id'])
            # gather the formulated text and post the media tweet
            tweet_dict['media_id'] = media_ids
        elif 'img' in record['fields']:
            res = requests.get(record['fields']['img'])
            res.raise_for_status()
            uploadable = BytesIO(res.content)
            response = tw.upload_media(media=uploadable)
            tweet_dict['media_id'] = response['media_id']
        else:
            tweet_dict['media_id'] = None
        # the next five lines handle draft tweets intended to be part of a thread
        if 'reply_to_rid' in record['fields']:
            last_tweet = airtab.get(record['fields']['reply_to_rid'])
            status_id = last_tweet['fields']['tweet id']
            tweet_dict['in_reply_to_status_id'] = status_id
        else:
            tweet_dict['in_reply_to_status_id'] = None
        tweet = tw.update_status(status=tweet_dict['status'], media_ids=tweet_dict['media_id'],
                                 in_reply_to_status_id=tweet_dict['in_reply_to_status_id'])
        this_dict = {}
        this_dict['tweet id'] = tweet['id_str']
        this_dict['tweet json'] = str(tweet)
        airtab.update(record['id'], this_dict)
        data['value2'] = f"{tweet['text']}\nscheduled tweets script is done 👌\nIt took {round(time.time() - t0, 2)} seconds."


def main():
    data = {'value1': 'scheduled_tweets.py'}
    send_next(data)
    data['value3'] = 'success'
    ifttt_event_url = os.environ['IFTTT_WEBHOOKS_URL'].format('code_completed')
    requests.post(ifttt_event_url, json=data)


if __name__ == "__main__":
    main()
