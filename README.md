# Telegram Updates Tweets
This package monitors the number of participants in a telegram channel and can post gains/losses updates to twitter.
It requires a twitter API key and telegram API key.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install telegram_updates_tweets.

```bash
pip install telegram_updates_tweets
```

## Usage
The package is configured with a bunch of options.
```cmd
python -m telegram_updates_tweets --tweet-losses 100 --twitter-key OopN17481741985zgmRg0FVAOzC --twitter-secret VWyvs87I091508915HWAJDdb4XlwOLPkQXOTPbcETEV8HlvmnCx --twitter-access-token 1341085719874981434437-1zh50lhr3WEJhjfabfhdK8oYGrSh3eW --twitter-access-token-secret 5jGpCn79Z8714871kjlafjagaXr7VKeNEKWQVzzU --telegram-api-id 2015515 --telegram-api-hash b7dae63689015901efeffc69 --mongodb 127.0.0.1:27017 --telegram-channel-name CHANNELNAME --tweet-loss-template 'Der Telegram Kanal hat {loss_step} Leser verloren und ist jetzt bei {count}' --tweet-graph-template '24h Bericht, aktuelle Anzahl der Leser ist {count}, Änderung {total_change:+d} Leser' --tweet-graph 20 --tweet-graph-img-template 'Innerhalb der letzten {hours} Std.: {total_change:+d} Leser'
```

## Options
```text
Usage: python -m telegram_updates_tweets [OPTIONS]

  Connects to telegram as a user and checks every 60minutes the subscriber
  count of the given channel. It allows to tweet gains and/or losses with
  additional info.

Options:
  --tweet-gains INTEGER           Deactivated if <=0, otherwise describes the
                                  step. Example: 100 -> tweet at 1900, 2000,
                                  2100, ...

  --tweet-losses INTEGER          Deactivated if <=0, otherwise describes the
                                  step. Example: 100 -> tweet at 2100, 2000,
                                  1900, ...

  --tweet-loss-template TEXT      This template will be formatted and posted
                                  on loss

  --tweet-gain-template TEXT      This template will be formatted and posted
                                  on gain

  --tweet-graph INTEGER           Deactivated if <0, otherwise 0..23 specifies
                                  the time when to post a 24h summary graph
                                  (requires mongodb)

  --tweet-graph-template TEXT     This template will be formatted and posted
                                  if --tweet-graph is specified

  --tweet-graph-img-template TEXT
                                  This template will be formatted and used in
                                  the image if --tweet-graph is specified

  --twitter-key TEXT              Also called API key, is created by the
                                  twitter app

  --twitter-secret TEXT           The secret of the twitter app
  --twitter-access-token TEXT     The access token of the oauth procedure
  --twitter-access-token-secret TEXT
                                  The secret of the oauth access token
  --telegram-api-id INTEGER       The number created by telegram
  --telegram-api-hash TEXT        The api hash created by telegram
  --telegram-channel-name TEXT    The name of the channel of interest
  --mongodb TEXT                  IP:PORT of the mongo db, if not set, no data
                                  will be logged

  --help                          Show this message and exit.
```

## Development
1. After cloning this repo execute `git config core.hooksPath hooks` in the root directory.
2. Install poetry https://python-poetry.org/docs/
3. `poetry config settings.virtualenvs.in-project true`
4. `poetry install`
4. `poetry shell`

## API keys
To use this package a twitter API key and a telegram API key are needed, these keys will be used to request OAUTH tokens from one twitter account and a telegram account.

1. Create a twitter APP with 'write' permission https://developer.twitter.com/en/portal/projects-and-apps
- this creates the `--twitter-key` and the ` --twitter-secret`
- the application will print a `authorization link`, open it, give permission to your own app the use your twitter profile
- it will print the `--twitter-access-token` and `--twitter-access-token-secret`
- all subsequent calls should use all four parameters
2. Create a telegram APP as described in https://core.telegram.org/api/obtaining_api_id
- this generates a `--telegram-api-id` (numbers) and `--telegram-api-hash` (string)
- when the appication is started with this parameters, it will ask for your phone number, you will receive a code from telegram, enter it in the application
- this will create a token file called 'anon.session' and 'anon.session-jornal'
- all subsequent calls should not prompt for other info
## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
