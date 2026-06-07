# Twitter Monitor

Monitor the `following`, `tweet`, ~~`like`~~ and `profile` of a Twitter user and send the changes to the telegram channel.

Data is crawled from Twitter web’s GraphQL API.

(Due to the unstable return results of Twitter Web's `following` API, accounts with more than 100 followings are not recommended to use `following` monitor.)

## Usage

### Setup

(Requires **python >= 3.10**)

Clone code and install dependent pip packages

```bash
git clone https://github.com/ionic-bond/twitter-monitor.git
cd twitter-monitor
pip3 install -r ./requirements.txt
```

### Prepare required tokens

- Create a Telegram bot and get it's token:

  https://t.me/BotFather

- Unofficial Twitter account auth:

    You need to prepare one or more normal twitter accounts, and then use the following command to generate auth cookies

    ```bash
    python3 main.py generate-auth-cookie --username "{username}" --password "{password}"
    ```

### Fill in config

- First make a copy from the config templates

  ```bash
  cp ./config/token.json.template ./config/token.json
  cp ./config/monitoring.json.template ./config/monitoring.json
  ```

- Edit `config/token.json`

  1. Fill in `telegram_bot_token`

  2. Fill in `twitter_auth_username_list` according to your prepared Twitter account auth

  3. Now you can test whether the tokens can be used by
      ```bash
      python3 main.py check-tokens
      ```

- Edit `config/monitoring.json`

  (You need to fill in some telegram chat id here, you can get them from https://t.me/userinfobot and https://t.me/myidbot)

  1. If you need to view monitor health information (starting summary, daily summary, alert), fill in `maintainer_chat_id`

  2. Fill in one or more user to `monitoring_user_list`, and their notification telegram chat id, weight, which monitors to enable. The greater the weight, the higher the query frequency. The **profile monitor** is forced to enable (because it triggers the other 3 monitors), and the other 3 monitors are free to choose whether to enable or not

  3. You can check if your telegram token and chat id are correct by
      ```bash
      python3 main.py check-tokens --telegram_chat_id {your_chat_id}
      ```

### Run

```bash
python3 main.py run
```
|         Flag          | Default |                        Description                        |
| :-------------------: | :-----: | :-------------------------------------------------------: |
|      --interval       |   15    |                   Monitor run interval                    |
|       --confirm       |  False  |     Confirm with the maintainer during initialization     |
| --listen_exit_command |  False  | Liten the "exit" command from telegram maintainer chat id |
| --send_daily_summary  |  False  |         Send daily summary to telegram maintainer         |

## Contact me

Telegram: [@ionic_bond](https://t.me/ionic_bond)

## Donate

[PayPal Donate](https://www.paypal.com/donate/?hosted_button_id=D5DRBK9BL6DUA) or [PayPal](https://paypal.me/ionicbond3)

## Pairing with GetXAPI for Cheaper Read Operations (Optional)

For users who need a cheaper or higher-rate-limit option for read-only Twitter (X) operations such as tweet search, profile lookup, and follower lists, this project can be paired with [GetXAPI](https://getxapi.com), a budget Twitter / X data API priced at $0.05 per 1K tweets versus the official X API basic tier at $200 / month.

Two integration patterns:

1. **Run side-by-side in your AI client.** Keep this project for its primary workflow and add the [official GetXAPI MCP server](https://github.com/getxapi/getxapi-mcp) for read-heavy tasks. Each tool name routes to the backend best suited for that operation.

2. **Add a backend toggle.** For a code-level reference of an optional alternative backend behind a single env variable, see the [PR pattern merged into a sibling project](https://github.com/GenAIwithMS/twitter-mcp/pull/3).

GetXAPI quick start:

- Signup with $0.50 free credit (no card required): https://getxapi.com/signup
- Official GetXAPI MCP server: https://github.com/getxapi/getxapi-mcp
- npm: `@getxapi/mcp`
- Pay-per-call pricing: $0.001 / call, $0.05 / 1K tweets

This pairing is fully optional. No behavior change for existing users.

