#!/usr/bin/env python
# -*- coding: utf-8 -*-
from yeelight import Bulb, BulbException
import logging
import time
import pytz
import subprocess
from astral import Astral
from datetime import date, datetime, timedelta


class Runner():
    def __init__(self, city, target_ip, bulb):
        a = Astral()
        a.solar_depression = 'civil'
        self.target_ip = target_ip
        self.city = a[city]
        self.bulb = Bulb(bulb)
        self.__turned_on__ = self.get_state() or False

        self.sunrise = None
        self.sunset = None
        self.set_sun()

        self.logger = logging.getLogger('yee')
        formatter = logging.Formatter('%(asctime)-15s %(message)s')
        fh = logging.FileHandler('yee.log')
        ch = logging.StreamHandler()

        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        self.logger.info('START with current state: %s', 'on' if self.__turned_on__ else 'off')

    def get_state(self):
        try:
            return self.bulb.get_properties()['power'] == 'on'
        except BulbException:
            return None

    def toggle(self):
        try:
            self.bulb.toggle()
            self.__turned_on__ = not self.__turned_on__
        except BulbException:
            pass

    @property
    def turned_on(self):
        state = self.get_state()
        return self.__turned_on__ if state is None else state

    @property
    def is_up(self):
        ret = subprocess.call(['ping', '-c', '5', '-W', '3', self.target_ip], stdout=open('/dev/null', 'w'),
                              stderr=open('/dev/null', 'w'))
        return ret == 0
        # return True if os.system("ping -c 1 " + self.target_ip) is 0 else False

    def check(self):
        tz = pytz.timezone('Europe/Samara')
        now = tz.localize(datetime.now())

        # sun is up - wait until next day
        if not self.sunset < now < self.sunrise:
            # turn off if it still up
            if self.turned_on:
                self.logger.info('turned OFF: %s', 'sunrise')
                self.toggle()
            self.set_sun()
            delay = (self.sunrise - now).seconds
            self.logger.info('sleep for : %s', delay)
            time.sleep(delay)
            return self.check()

        # pc is powered off - shut down bulb
        # check every minute
        if not self.is_up:
            if self.turned_on:
                self.logger.info('turned OFF: %s', 'pc is down')
                self.toggle()
            time.sleep(60)
            return self.check()

        # sun is down
        # pc is up
        # bulb should turned on
        # check every minute
        if not self.turned_on:
            self.logger.info('turned ON: %s', 'default state')
            self.toggle()
        time.sleep(60)
        return self.check()

    def set_sun(self):
        self.sunrise = self.city.sun(date=date.today() + timedelta(1), local=True)['sunrise']
        self.sunset = self.city.sun(date=date.today(), local=True)['sunset']

    def run(self):
        self.check()


if __name__ == '__main__':
    r = Runner(
        target_ip='192.168.1.2',
        bulb="192.168.1.130",
        city='Moscow'
    )
    r.run()
