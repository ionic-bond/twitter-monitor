# Twitter Monitor

Monitor the `following`, `tweet`, `like` and `profile` of a Twitter user and send the changes to the telegram channel.

(Because the twitter api only allows to query the last 200 **user liked tweets** sorted by creation time, we cannot know if **the user likes a very old tweet**.)

## List of deployed channels

(Mainly hololive vtuber)

- 湊あくあ(minatoaqua): https://t.me/minatoaqua_twitter_monitor
  <details>
    <summary></summary>
    りんちゃん(rinchan_nanoda): https://t.me/rinchan_twitter_monitor
  </details>

- ~~潤羽るしあ(uruharushia): https://t.me/uruharushia_twitter_monitor~~  
  <details>
    <summary></summary>
    みけねこ(95rn16): https://t.me/mikeneko_twitter_monitor
  </details>

- 兎田ぺこら(usadapekora): https://t.me/usadapekora_twitter_monitor

- 姫森ルーナ(himemoriluna): https://t.me/himemoriluna_twitter_monitor

- さくらみこ(sakuramiko35): https://t.me/sakuramiko_twitter_monitor

- 紫咲シオン(murasakishionch): https://t.me/murasakishion_twitter_monitor

- Gawr Gura(gawrgura): https://t.me/gawrgura_twitter_monitor

- 宝鐘マリン(houshoumarine): https://t.me/houshoumarine_twitter_monitor

- 沙花叉クロヱ(sakamatachloe): https://t.me/sakamatachloe_twitter_monitor

- <details>
  <summary></summary>
  rurudo(rurudo_): https://t.me/rurudo_twitter_monitor
</details>

(Welcome to commit new channels)

## Usage

### Setup

(Requires **python >= 3.8**)

Clone code and install dependent pip packages

```bash
git clone https://github.com/ionic-bond/twitter-monitor.git
cd twitter-monitor
pip3 install ./requirements.txt
```

### Prepare required tokens

- Create a Telegram bot and get it's token:

  https://t.me/BotFather

- Twitter API auth:

  You have 2 ways to get Twitter API auth:

  1. Official Twitter API bearer token

      Your can buy it on https://developer.twitter.com/en/portal/petition/essential/basic-info

      (No longer maintained because Elon deactivated all my free tokens)

  2. Unofficial Twitter account auth by [tweepy-authlib](https://github.com/tsukumijima/tweepy-authlib)

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

  2. Fill in one of `twitter_bearer_token_list` and `twitter_auth_username_list` according to your prepared Twitter API auth

  3. Now you can test whether the tokens can be used by
      ```bash
      python3 main.py check-tokens
      ```

- Edit `config/monitoring.json`

  (You need to fill in some telegram chat id here, you can get them from https://t.me/userinfobot and https://t.me/myidbot)

  1. If you need to view monitor health information (starting summary, daily summary, alert), fill in `maintainer_chat_id`

  2. If you want to reduce the frequency of monitor access to Twitter API, increase `weight_sum_offset`

  3. Fill in one or more user to `monitoring_user_list`, and their notification telegram chat id, weight, which monitors to enable. The greater the weight, the higher the query frequency. The **profile monitor** is forced to enable (because it triggers the other 3 monitors), and the other 3 monitors are free to choose whether to enable or not

  4. You can check if your telegram token and chat id are correct by
      ```bash
      python3 main.py check-tokens --telegram_chat_id {your_chat_id}
      ```

### Run

```bash
python3 main.py run
```
|         Flag          | Default |                        Description                        |
| :-------------------: | :-----: | :-------------------------------------------------------: |
|       --confirm       |  False  |     Confirm with the maintainer during initialization     |
| --listen_exit_command |  False  | Liten the "exit" command from telegram maintainer chat id |
| --send_daily_summary  |  False  |         Send daily summary to telegram maintainer         |

## Contact me

Telegram: [@ionic_bond](https://t.me/ionic_bond)
