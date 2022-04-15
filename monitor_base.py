#!/usr/bin/python3

from abc import ABC, abstractmethod


class MonitorBase(ABC):

    @abstractmethod
    def watch(self):
        pass

    @abstractmethod
    def status(self) -> str:
        pass
