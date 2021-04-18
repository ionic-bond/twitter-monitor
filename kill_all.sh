ps -ef | grep 'TwitterUserMonitor' | grep -v 'grep' | cut -c 9-16 | xargs kill -9
