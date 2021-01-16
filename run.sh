cd `dirname $0`
ps -ef | grep 'twitter_following_monitor' | grep -v 'grep' | cut -c 9-16 | xargs kill -9
# setsid python3 ./twitter_following_monitor.py run --username ionicbond3 --log_path ~/ion_monitor.log &
setsid python3 ./twitter_following_monitor.py run --username minatoaqua --log_path ~/aqua_monitor.log &
setsid python3 ./twitter_following_monitor.py run --username uruharushia --log_path ~/rushia_monitor.log &
