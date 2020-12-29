ps -ef | grep 'twitter_following_monitor' | grep -v 'grep' | cut -c 9-15 | xargs kill -9
# setsid python3 ./twitter_following_monitor.py run --username ionicbond3 --log_path ~/ion_monitor.log
setsid python3 ./twitter_following_monitor.py run --username minatoaqua --log_path ~/aqua_monitor.log
