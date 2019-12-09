# !/usr/bin/env python3
import time
from io import BytesIO
import os
import requests
from airtable import Airtable
from documentcloud import DocumentCloud
from twython import Twython

dc = DocumentCloud(
    os.environ['DOCUMENT_CLOUD_USERNAME'], os.environ['DOCUMENT_CLOUD_PW'])
tw = Twython(os.environ['TWITTER_APP_KEY'], os.environ['TWITTER_APP_SECRET'],
             os.environ['TWITTER_OAUTH_TOKEN'], os.environ['TWITTER_OAUTH_TOKEN_SECRET'])
airtab = Airtable(os.environ['botfeldman89_db'],
                  'scheduled_tweets', os.environ['AIRTABLE_API_KEY'])
airtab_log = Airtable(os.environ['log_db'],
                      'log', os.environ['AIRTABLE_API_KEY'])


def wrap_it_up(t0, new, total=None, function=None):
    this_dict = {'module': 'scheduled_tweets.py'}
    this_dict['function'] = function
    this_dict['duration'] = round((time.time() - t0) / 60, 2)
    this_dict['total'] = total
    this_dict['new'] = new
    airtab_log.insert(this_dict, typecast=True)


def upload_dc_images(dc_id):
    media_ids = []
    obj = dc.documents.get(dc_id)
    image_list = obj.normal_image_url_list[:4]
    for image in image_list:
        res = requests.get(image)
        res.raise_for_status()
        uploadable = BytesIO(res.content)
        response = tw.upload_media(media=uploadable)
        media_ids.append(response['media_id'])
        return media_ids


def upload_img_from_table(img):
    res = requests.get(img)
    res.raise_for_status()
    uploadable = BytesIO(res.content)
    response = tw.upload_media(media=uploadable)
    return response['media_id']


def thread_or_not(record):
    if 'reply_to_rid' in record['fields']:
        last_tweet = airtab.get(record['fields']['reply_to_rid'])
        status_id = last_tweet['fields']['tweet id']
        return status_id
    return None


def send_next():
    results = airtab.get_all(view='not yet tweeted')
    if results:
        record = results[0]
        tweet_dict = {'status': record['fields']['msg']}
        if record['fields']['re'] == "clippings":
            tweet_dict['media_id'] = upload_dc_images(
                record['fields']['dc_id'])
        elif 'img' in record['fields']:
            tweet_dict['media_id'] = upload_img_from_table(
                record['fields']['img'])
        else:
            tweet_dict['media_id'] = None
        tweet_dict['in_reply_to_status_id'] = thread_or_not(record)
        tweet = tw.update_status(status=tweet_dict['status'],
                                 media_ids=tweet_dict['media_id'],
                                 in_reply_to_status_id=tweet_dict['in_reply_to_status_id'])
        return record['id'], tweet
    return None


def update_tweets_airtable(rid, tweet):
    this_dict = {}
    this_dict['tweet id'] = tweet['id_str']
    this_dict['tweet json'] = str(tweet)
    airtab.update(rid, this_dict)


def main():
    t0, i = time.time(), 0
    response = send_next()
    if response:
        rid, twitter_data = response
        update_tweets_airtable(rid, twitter_data)
        i = 1
    wrap_it_up(t0, i)


if __name__ == "__main__":
    main()
