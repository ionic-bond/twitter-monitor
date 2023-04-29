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

## How to deploy

### Apply for required token

- Twitter dev API token:

  https://developer.twitter.com/en/apply-for-access

- Create a Telegram bot and get token:

  https://t.me/BotFather

### Deploy

Requires **python >= 3.8**

- Clone code and install dependent pip packages

  ```bash
  git clone https://github.com/ionic-bond/twitter-monitor.git
  cd twitter-monitor
  pip3 install ./requirements.txt
  ```

- Copy the config templates and fill in them

  ```
  cp ./config/token.json.template ./config/token.json
  cp ./config/monitoring.json.template ./config/monitoring.json
  ```
  
  First fill in your **Twitter API bearer token** and **Telegram bot token** to `./config/token.json`
  
  Then you can test whether the tokens can be used by
  
  ```
  python3 main.py check-token --telegram_chat_id {your_telegram_chat_id}
  ```

(writing, not finished)

## Contact me

Telegram: [@ionic_bond](https://t.me/ionic_bond)
