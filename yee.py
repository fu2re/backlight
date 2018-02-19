#!/usr/bin/env python
# -*- coding: utf-8 -*-
from yeelight import Bulb, BulbException
import os
import logging
import time
from astral import Astral
from datetime import date, datetime, timedelta

FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)


class Runner():
    def __init__(self, city, target_ip, bulb):
        a = Astral()
        a.solar_depression = 'civil'
        self.target_ip = target_ip
        self.city = a[city]
        self.bulb = Bulb(bulb)
        self.turned_on = self.get_state()

        self.sunrise = None
        self.sunset = None
        self.set_sun()

    def get_state(self):
        try:
            return self.bulb.get_properties()['power'] == 'on'
        except BulbException:
            return False

    def toggle(self):
        try:
            self.bulb.toggle()
            self.turned_on = not self.turned_on
        except BulbException:
            pass

    @property
    def is_up(self):
        return True if os.system("ping -c 1 " + self.target_ip) is 0 else False

    def check(self):
        now = datetime.now()

        # sun is up - wait until next day
        if not (now > self.sun['sunset'] and now < self.sun['sunrise']):
            # turn off if it still up
            if self.turned_on:
                self.toggle()
            self.set_sun()
            time.sleep((self.sunrise - now).seconds)
            return self.check()

        # pc is powered off - shut down bulb
        # check every minute
        if not self.is_up:
            if self.turned_on:
                self.toggle()
            time.sleep(60)
            return self.check()

        # sun is down
        # pc is up
        # bulb should turned on
        # check every minute
        if not self.turned_on:
            logging.info('Protocol problem: %s', 'connection reset', extra=d)
            self.toggle()
        time.sleep(60)
        return self.check()

    def set_sun(self):
        self.sunrise = self.city.sun(date=date.today() + timedelta(1), local=True)['sunrise']
        self.sunset = self.city.sun(date=date.today(), local=True)['sunset']



    def run(self):
        pass

if module.__name__ == '__main__':
    r = Runner(
        target_ip='192.168.1.2',
        bulb="192.168.1.130",
        city='Moscow'
    )
    r.run()
