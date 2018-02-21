#!/usr/bin/env python
# -*- coding: utf-8 -*-
from yeelight import Bulb, BulbException
import logging
import time
import pytz
import subprocess
from datetime import datetime, timedelta
from astral import Location
from colour import Color


class Runner(object):
    def __init__(self,
                 target_ip, bulb,
                 delta,
                 tz, lat, long,
                 location_name='Location',
                 region_name='Russia',
                 elevation=0,
                 color=((255, 255, 255), (225, 143, 0)),
                 brightness=(17, 50)):
        # ip address of target PC
        self.target_ip = target_ip
        # bulb attached to this pc
        self.bulb = bulb
        # check the current state
        self.__turned_on__ = self.turned_on

        # sunset offset percentage between dusk and sunset, when bulb is turn on
        self.delta = delta

        # color and brightness gradient for sunrise effect
        self.grad = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in list(Color(
            rgb=(
                color[0][0] / 255,
                color[0][1] / 255,
                color[0][2] / 255
            )
        ).range_to(Color(
            rgb=(
                color[1][0] / 255,
                color[1][1] / 255,
                color[1][2] / 255
            )
        ), 30))]
        self.brightness = range(*brightness) if brightness[1] > brightness[0] else \
            list(reversed(range(*list(reversed(brightness)))))

        # setup current location and timezone
        self.tz = pytz.timezone(tz)
        self.location = Location((location_name, region_name, lat, long, tz, elevation))
        self.dusk = None
        self.sunrise = None
        self.sunset = None
        self.set_sun()

        # logging
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
        """
        toggle bulb power state
        :param state:
        :param retry:
        :return:
        """
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

    def upd(self, retry=3):
        """
        update the current bulb colour and brightness
        :param retry:
        :return:
        """
        try:
            progress = max((self.now - self.sunset).seconds / (self.dusk - self.sunset).seconds, 1)
            bulb = Bulb(self.bulb)
            bulb.set_rgb(*self.grad[min(int(progress * len(self.grad)), len(self.grad) - 1)])
            bulb.set_brightness(self.brightness[min(int(progress * len(self.brightness)), len(self.grad) - 1)])
        except BulbException:
            time.sleep(10)
            if retry > 0:
                return self.upd(retry - 1)

    def get_state(self, retry=3):
        """
        get the current bulb state
        :return:
        """
        try:
            return Bulb(self.bulb).get_properties()['power']
        except BulbException:
            time.sleep(10)
            return self.get_state(retry-1) if retry > 0 else None

    @property
    def turned_on(self):
        """
        check the current bulb power state
        :return:
        boolean
        """
        state = self.get_state()
        return self.__turned_on__ if (state is None) else state == 'on'

    @property
    def is_up(self):
        ret = subprocess.call(['ping', '-c', '5', '-W', '3', self.target_ip], stdout=open('/dev/null', 'w'),
                              stderr=open('/dev/null', 'w'))
        return ret == 0

    @property
    def now(self):
        return self.tz.fromutc(datetime.utcnow())

    def check(self):
        now = self.now

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

        # try to set colour BEFORE turn the bulb on
        if self.sunset < now < self.dusk:
            self.upd()

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
        """
        update data
        :return:
        """
        now = self.now
        i1, i2 = self.location.sun(now), self.location.sun(now + timedelta(1))
        self.dusk = i1['dusk']
        self.sunset = i1['sunset'] + timedelta(seconds=int((self.dusk - i1['sunset']).seconds * self.delta))
        self.sunrise = i2['sunrise']

    def run(self):
        self.check()


if __name__ == '__main__':
    r = Runner(
        target_ip='192.168.1.2',
        bulb="192.168.1.130",
        lat=54.19, long=48.23,
        tz='Europe/Samara',
        location_name='Ulyanovsk',
        region_name='Russia',
        elevation=150,
        delta=0.07,
        color=((255, 255, 255), (225, 143, 0)),
        brightness=(10, 40)
    )
    r.run()
