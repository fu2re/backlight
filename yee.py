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
    def __init__(self, target_ip, bulb):
        a = Astral()
        a.solar_depression = 'civil'
        self.target_ip = target_ip
        self.city = a['Moscow']
        self.bulb = bulb
        self.__turned_on__ = self.turned_on

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

    def toggle(self, state=None, retry=3):
        try:
            bulb = Bulb(self.bulb)
            if state is False:
                bulb.turn_off()
                self.__turned_on__ = False
            elif state is True:
                bulb.turn_on()
                self.__turned_on__ = True
            else:
                bulb.toggle()
                self.__turned_on__ = not self.__turned_on__
        except BulbException:
            time.sleep(10)
            if retry > 0:
                return self.toggle(state, retry - 1)

    def get_state(self, retry=3):
        try:
            return Bulb(self.bulb).get_properties()['power']
        except BulbException:
            time.sleep(10)
            return self.get_state(retry-1) if retry > 0 else None

    @property
    def turned_on(self):
        state = self.get_state()
        return self.__turned_on__ if (state is None) else state == 'on'

    @property
    def is_up(self):
        ret = subprocess.call(['ping', '-c', '5', '-W', '3', self.target_ip], stdout=open('/dev/null', 'w'),
                              stderr=open('/dev/null', 'w'))
        return ret == 0

    def check(self):
        tz = pytz.timezone('Europe/Samara')
        now = tz.localize(datetime.now()).astimezone(pytz.timezone('Europe/Moscow'))

        # sun is up - wait until next day
        if not self.sunset < now < self.sunrise:
            # turn off if it still up
            if self.turned_on:
                self.logger.info('turned OFF: %s', 'sunrise')
                self.toggle(False)
            # sleep until next sunset
            self.set_sun()
            delay = (self.sunset - now).seconds
            self.logger.info('sleep for : %s', delay)
            time.sleep(delay)
            return self.check()

        # pc is powered off - shut down bulb
        # check every minute
        if not self.is_up:
            if self.turned_on:
                self.logger.info('turned OFF: %s', 'pc is down')
                self.toggle(False)
            time.sleep(60)
            return self.check()

        # sun is down
        # pc is up
        # bulb should turned on
        # check every minute
        if not self.turned_on:
            self.logger.info('turned ON: %s', 'default state')
            self.toggle(True)
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
        bulb="192.168.1.130"
    )
    r.run()
