import logging
from datetime import datetime, timedelta, timezone


class StatusTracker():

    def __new__(self):
        raise Exception('Do not instantiate this class!')

    monitors_status = dict()
    notifiers_status = dict()

    logger = logging.getLogger('status')

    @classmethod
    def update_monitor_status(cls, monitor_type: str, username: str):
        key = '{}-{}'.format(monitor_type, username)
        cls.monitors_status[key] = datetime.now(timezone.utc)

    @classmethod
    def get_monitor_status(cls, monitor_type: str, username: str):
        key = '{}-{}'.format(monitor_type, username)
        return cls.monitors_status.get(key, None)

    @classmethod
    def set_notifier_status(cls, notifier: str, status: bool):
        cls.notifiers_status[notifier] = status

    @classmethod
    def check(cls) -> list:
        alerts = []

        monitor_time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        for monitor_name, monitor_status in cls.monitors_status.items():
            cls.logger.info('{}: {}'.format(monitor_name, monitor_status))
            if monitor_status < monitor_time_threshold:
                alerts.append('{}: {}'.format(monitor_name, monitor_status))

        for notifier_name, notifier_status in cls.notifiers_status.items():
            cls.logger.info('{}: {}'.format(notifier_name, notifier_status))
            if notifier_status is False:
                alerts.append('{}'.format(notifier_name))

        return alerts
