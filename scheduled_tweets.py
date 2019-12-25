# !/usr/bin/env python3
import time
from io import BytesIO
import requests
from common import airtab_tweets as airtab, dc, tw, wrap_from_module


wrap_it_up = wrap_from_module('scheduled_tweets')


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
            tweet_dict['media_id'] = upload_dc_images(record['fields']['dc_id'])
        elif 'img' in record['fields']:
            tweet_dict['media_id'] = upload_img_from_table(record['fields']['img'])
        else:
            tweet_dict['media_id'] = None
        tweet_dict['in_reply_to_status_id'] = thread_or_not(record)
        tweet = tw.update_status(status=tweet_dict['status'],
                                 media_ids=tweet_dict['media_id'],
                                 in_reply_to_status_id=tweet_dict['in_reply_to_status_id'])
        return record['id'], tweet, len(results)
    return None


def update_tweets_airtable(rid, tweet):
    this_dict = {}
    this_dict['tweet id'] = tweet['id_str']
    this_dict['tweet json'] = str(tweet)
    airtab.update(rid, this_dict)


def main():
    t0, i, total = time.time(), 0, 0
    response = send_next()
    if response:
        rid, twitter_data, total = response
        update_tweets_airtable(rid, twitter_data)
        i = 1
    wrap_it_up(t0, i, total, 'scheduled_tweets.main')


if __name__ == "__main__":
    main()
