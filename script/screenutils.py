#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Note: this may not work with bpython, use python 2.6 or upper
# Author: Christophe Narbonne
# Contrib: Alexis Metaireau
from subprocess import getoutput
from multiprocessing import Process
from os import system
from time import sleep


def list_screens():
    """List all the existing screens and build a Screen instance for each
    """
    return [Screen(".".join(l.split(".")[1:]).split("\t")[0])
                for l in getoutput("screen -ls | grep -P '\t'").split('\n')]


class ScreenNotFoundError(Exception):
    """raised when the screen does not exists"""


class Screen(object):
    """Represents a gnu-screen object::

        >>> s=Screen("screenName", create=True)
        >>> s.name
        'screenName'
        >>> s.exists
        True
        >>> s.state
        >>> s.send_commands("man -k keyboard")
        >>> s.kill()
        >>> s.exists
        False
    """

    def __init__(self, name, create=False):
        self.name = name
        self._id = None
        self._status = None
        if create:
            self.create()

    @property
    def id(self):
        """return the identifier of the screen"""
        if not self._id:
            self._set_screen_infos()
        return self._id

    @property
    def status(self):
        """return the status of the screen"""
        self._set_screen_infos()
        return self._status

    @property
    def exists(self):
        """Tell if the screen session exists or not."""
        # output line sample:
        # "     28062.G.Terminal        (Detached)"
        lines = getoutput("screen -ls | grep " + self.name).split('\n')
        return self.name in [".".join(l.split(".")[1:]).split("\t")[0]
                             for l in lines]

    def create(self):
        """create a screen, if does not exists yet"""
        if not self.exists:
            Process(target=self._delayed_detach).start()
            system('screen -UR ' + self.name)

    def interrupt(self):
        """Insert CTRL+C in the screen session"""
        self._check_exists()
        system("screen -x " + self.name + " -X eval \"stuff \\003\"")

    def kill(self):
        """Kill the screen applications then quit the screen"""
        self._check_exists()
        system('screen -x ' + self.name + ' -X quit')

    def detach(self):
        """detach the screen"""
        self._check_exists()
        system("screen -d " + self.name)

    def _delayed_detach(self):
        sleep(5)
        self.detach()

    def send_commands(self, commands):
        """send commands to the active gnu-screen"""
        self._check_exists()
        for command in commands:
            sleep(0.02)
            print(command)
            system('screen -x ' + self.name + ' -X stuff "' + command + '" ')
            sleep(0.02)
            system('screen -x ' + self.name + ' -X eval "stuff \\015" ')

    def _check_exists(self, message="Error code: 404"):
        """check whereas the screen exist. if not, raise an exception"""
        if not self.exists:
            raise ScreenNotFoundError(message)

    def _set_screen_infos(self):
        """set the screen information related parameters"""
        if self.exists:
            infos = getoutput("screen -ls | grep %s" % self.name).split('\t')[1:]
            self._id = infos[0].split('.')[0]
            self._date = infos[1][1:-1]
            self._status = infos[2][1:-1]

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.name)

