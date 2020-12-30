import re
from datetime import datetime
from time import sleep

import click
import pymongo
import tweepy
from telethon import TelegramClient, sync
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest


@click.command()
@click.option(
    "--tweet-gains",
    default=-1,
    help="Deactivated if <=0, otherwise describes the step. Example: 100 -> tweet at 1900, 2000, 2100, ...",
)
@click.option(
    "--tweet-losses",
    default=-1,
    help="Deactivated if <=0, otherwise describes the step. Example: 100 -> tweet at 2100, 2000, 1900, ...",
)
@click.option("--tweet-loss-template", type=str, default='The channel `{channel_name}` lost {loss_step} subscribers and is at {count} currently', help="This template will be formatted and posted on loss")
@click.option("--tweet-gain-template", type=str, default='The channel `{channel_name}` gained {gain_step} subscribers and is at {count} currently',help="This template will be formatted and posted on gain")
@click.option("--twitter-key", type=str, help="Also called API key, is created by the twitter app")
@click.option("--twitter-secret", type=str, help="The secret of the twitter app")
@click.option("--twitter-access-token", type=str, help="The access token of the oauth procedure")
@click.option("--twitter-access-token-secret", type=str, help="The secret of the oauth access token")
@click.option("--telegram-api-id", type=int, help="The number created by telegram")
@click.option("--telegram-api-hash", type=str, help="The api hash created by telegram")
@click.option("--telegram-channel-name", type=str, help="The name of the channel of interest")
@click.option("--mongodb", type=str, help="IP:PORT of the mongo db, if not set, no data will be logged")
def main(
    tweet_gains,
    tweet_losses,
    tweet_loss_template,
    tweet_gain_template,
    twitter_key,
    twitter_secret,
    twitter_access_token,
    twitter_access_token_secret,
    telegram_api_id,
    telegram_api_hash,
    telegram_channel_name,
    mongodb,
):
    """Connects to telegram as a user and checks every 60minutes the subscriber count of the given channel.
    It allows to tweet gains and/or losses with additional info. It has a small web interface to configure access to social media."""

    # twitter
    auth = tweepy.OAuthHandler(twitter_key, twitter_secret)
    # auth.set_access_token("622518493-6VcLIPprbQbv9wkcBBPvCle8vsjU9fE85Dq9oStl", "tH9aKQbQQ1iRdYTcLSsPwitl44BkAc6jilrsU0ifnXvZhq")
    if twitter_access_token is None:
        redirect_url = auth.get_authorization_url()
        fprint("Open the link:", redirect_url)
        verifier = input("Enter verifier: ")
        token = auth.request_token["oauth_token"]
        auth.request_token = {"oauth_token": token, "oauth_token_secret": verifier}
        auth.get_access_token(verifier)
        fprint("--twitter-access-token", auth.access_token)
        fprint("--twitter-access-token-secret", auth.access_token_secret)
    else:
        auth.set_access_token(twitter_access_token, twitter_access_token_secret)

    tw = tweepy.API(auth)
    tw_client_id = tw.me().id
    try:
        last_tweet = tw.user_timeline(id=tw_client_id, count=1)[0]
    except:
        last_tweet = ''

    # telegram
    tl = TelegramClient("anon", telegram_api_id, telegram_api_hash).start()

    def get_count():
        tw_channel = tl(GetFullChannelRequest(channel=telegram_channel_name))
        return tw_channel.full_chat.participants_count

    # mongo db
    if mongodb:
        mongo_client = pymongo.MongoClient("mongodb://"+mongodb)
        mongo_db = mongo_client["telegram_updates_tweets"]
        mongo_col = mongo_db[telegram_channel_name]
        fprint('number of datapoints in mongodb:', mongo_col.estimated_document_count())

    c = get_count()
    numbers = [int(x) for x in re.findall('[0-9]+', last_tweet.text)]
    if numbers:
        last_tweeted_num = min(numbers, key=lambda x:abs(x-c))
        fprint('last tweeted number:', last_tweeted_num)
    else:
        last_tweeted_num = c


    lower_threshold = None
    upper_threshold = None
    def update_thresholds():
        nonlocal lower_threshold
        nonlocal upper_threshold
        if tweet_losses>0:
            d,r = divmod(last_tweeted_num-1,tweet_losses)
            lower_threshold = d*tweet_losses
            fprint('new lower:', lower_threshold)
        if tweet_gains>0:
            d,r = divmod(last_tweeted_num+1,tweet_gains)
            upper_threshold = (d+1)*tweet_gains
            fprint('new upper:', upper_threshold)
    update_thresholds()

    def tweet(s, data, count):
        nonlocal last_tweeted_num
        formatted = s.format(**data)
        fprint('tweeting:',formatted)
        tw.update_status(formatted)
        last_tweeted_num = count
        update_thresholds()

    while True:
        # get count
        c = get_count()
        fprint('current participants:',c)

        # insert in database
        if mongodb:
            mongo_col.insert_one({"datetime": str(datetime.now()), "count": c})

        # check if threshold is triggered
        data = {'channel_name': telegram_channel_name, 'loss_step': tweet_losses, 'count':c, 'gain_step':tweet_gains}

        if upper_threshold and c > upper_threshold:
            tweet(tweet_gain_template, data, c)
        elif lower_threshold and c < lower_threshold:
            tweet(tweet_loss_template, data, c)

        sleep(60)

def fprint(*s):
    print(datetime.now(),*s)

if __name__ == "__main__":
    main()
