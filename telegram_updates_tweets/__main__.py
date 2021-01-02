import re
import traceback
from datetime import datetime, timedelta
from time import sleep

import click
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
@click.option(
    "--tweet-loss-template",
    type=str,
    default="The channel `{channel_name}` lost {loss_step} subscribers and is at {count} currently",
    help="This template will be formatted and posted on loss",
)
@click.option(
    "--tweet-gain-template",
    type=str,
    default="The channel `{channel_name}` gained {gain_step} subscribers and is at {count} currently",
    help="This template will be formatted and posted on gain",
)
@click.option(
    "--tweet-graph",
    type=int,
    default=-1,
    help="Deactivated if <0, otherwise 0..23 specifies the time when to post a 24h summary graph (requires mongodb)",
)
@click.option(
    "--tweet-graph-template",
    type=str,
    default="The channel `{channel_name}` is at {count} currently",
    help="This template will be formatted and posted if --tweet-graph is specified",
)
@click.option(
    "--tweet-graph-img-template",
    type=str,
    default="Within the last {hours}h: {total_change:+d} participants",
    help="This template will be formatted and used in the image if --tweet-graph is specified",
)
@click.option(
    "--monitoring-port",
    type=int,
    default=-1,
    help="Deactivated if <=0, otherwise 0..65000 specifies the port which allows to fetch monitoring information. Requires --monitoring-password",
)
@click.option(
    "--monitoring-password",
    type=str,
    help="Is required if --monitoring-port is set. Is used in basic authentication password, username can be any.",
)
@click.option(
    "--check-frequency",
    type=int,
    default=60,
    help="Check period in seconds",
)
@click.option("--twitter-key", type=str, help="Also called API key, is created by the twitter app")
@click.option("--twitter-secret", type=str, help="The secret of the twitter app")
@click.option("--twitter-access-token", type=str, help="The access token of the oauth procedure")
@click.option(
    "--twitter-access-token-secret",
    type=str,
    help="The secret of the oauth access token",
)
@click.option("--telegram-api-id", type=int, help="The number created by telegram")
@click.option("--telegram-api-hash", type=str, help="The api hash created by telegram")
@click.option("--telegram-channel-name", type=str, help="The name of the channel of interest")
@click.option(
    "--mongodb",
    type=str,
    help="IP:PORT of the mongo db, if not set, no data will be logged",
)
def main(
    tweet_gains,
    tweet_losses,
    tweet_graph,
    tweet_graph_template,
    tweet_graph_img_template,
    tweet_loss_template,
    tweet_gain_template,
    monitoring_port,
    monitoring_password,
    check_frequency,
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
    It allows to tweet gains and/or losses with additional info."""

    # twitter
    auth = tweepy.OAuthHandler(twitter_key, twitter_secret)

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
        last_tweet = ""

    # telegram
    tl = TelegramClient("anon", telegram_api_id, telegram_api_hash).start()

    c = 0
    last_update = None

    def get_count():
        nonlocal c
        nonlocal last_update
        tw_channel = tl(GetFullChannelRequest(channel=telegram_channel_name))
        c = tw_channel.full_chat.participants_count
        last_update = datetime.now()

    # mongo db
    if mongodb:
        import pymongo

        mongo_client = pymongo.MongoClient("mongodb://" + mongodb)
        mongo_db = mongo_client["telegram_updates_tweets"]
        mongo_col = mongo_db[telegram_channel_name]
        fprint("number of datapoints in mongodb:", mongo_col.estimated_document_count())

    # initial count of tl channel
    get_count()

    # monitoring
    if monitoring_port > 0:
        import threading
        from waitress import serve
        from flask import Flask, request

        app = Flask(__name__)

        @app.route("/")
        def hello_world():
            if request.authorization is None or request.authorization.password != monitoring_password:
                return "wrong password", 401
            nonlocal last_update
            time_diff = (datetime.now() - last_update).seconds
            return f"{time_diff:d} seconds since last check: " + ("OK" if time_diff < check_frequency * 2.1 else "ERROR")

        def monitoring_loop():
            serve(app, listen=f"*:{monitoring_port}")

        thread = threading.Thread(target=monitoring_loop)
        thread.setDaemon(True)
        thread.start()

    numbers = [int(x) for x in re.findall("[0-9]+", last_tweet.text)]
    if numbers:
        last_tweeted_num = min(numbers, key=lambda x: abs(x - c))
        fprint("last tweeted number:", last_tweeted_num)
    else:
        last_tweeted_num = c

    lower_threshold = None
    upper_threshold = None

    def update_thresholds():
        nonlocal lower_threshold
        nonlocal upper_threshold
        if tweet_losses > 0:
            d, r = divmod(last_tweeted_num - 1, tweet_losses)
            lower_threshold = d * tweet_losses
            fprint("new lower:", lower_threshold)
        if tweet_gains > 0:
            d, r = divmod(last_tweeted_num + 1, tweet_gains)
            upper_threshold = (d + 1) * tweet_gains
            fprint("new upper:", upper_threshold)

    update_thresholds()

    def tweet(s, data, count):
        nonlocal last_tweeted_num
        formatted = s.format(**data)
        fprint("tweeting:", formatted)
        tw.update_status(formatted)
        last_tweeted_num = count
        update_thresholds()

    if tweet_graph >= 0:
        from matplotlib import pyplot as plt

        def tweet_24h_graph(data):
            f = "temp.png"

            n = datetime.now()
            start = n - timedelta(days=1)
            query = {"datetime": {"$gte": str(start), "$lt": str(n)}}
            last_24h = mongo_col.find(query).sort([("datetime", pymongo.ASCENDING)])

            elements = list(last_24h)
            all_counts = [d["count"] for d in elements]
            all_times = [datetime.strptime(d["datetime"], "%Y-%m-%d %H:%M:%S.%f") for d in elements]
            plt.figure(figsize=(8, 4))
            plt.plot(all_times, all_counts)
            plt.grid()

            hours = round((all_times[-1] - all_times[0]).seconds / 3600)
            total_change = all_counts[-1] - all_counts[0]
            data.update({"hours": hours, "total_change": total_change})
            if tweet_graph_img_template:
                plt.title(tweet_graph_img_template.format(**data))

            plt.tight_layout()
            plt.savefig(f)

            formatted = tweet_graph_template.format(**data)
            fprint("tweeting:", formatted)
            tw.update_with_media(f, formatted)

    last_hour = -1
    while True:
        # get count
        get_count()
        fprint("current participants:", c)

        # insert in database
        if mongodb:
            mongo_col.insert_one({"datetime": str(datetime.now()), "count": c})

        # check if threshold is triggered
        data = {
            "channel_name": telegram_channel_name,
            "loss_step": tweet_losses,
            "count": c,
            "gain_step": tweet_gains,
        }

        # tweet report once at a specific hour
        hour = datetime.now().hour
        if hour == tweet_graph and last_hour == (hour - 1) % 24:
            tweet_24h_graph(data)
        last_hour = hour

        if upper_threshold and c > upper_threshold:
            tweet(tweet_gain_template, data, c)
        elif lower_threshold and c < lower_threshold:
            tweet(tweet_loss_template, data, c)

        sleep(60)


def fprint(*s):
    print(datetime.now(), *s)


if __name__ == "__main__":
    while True:
        try:
            main(prog_name="python -m telegram_updates_tweets")
        except KeyboardInterrupt:
            print("bye")
            break
        except SystemExit:
            break
        except Exception as e:
            fprint("Error:", str(e))
            traceback.print_stack()
            fprint("Sleeping 60s")
            try:
                sleep(60)
            except KeyboardInterrupt:
                print("bye")
                break
