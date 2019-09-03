#!/usr/bin/env python3
from gi.repository import Playerctl, GLib
import subprocess
import screeninfo
import requests
from PIL import Image, ImageDraw, ImageFilter
import io
import musicbrainzngs
import math
import random
import sounddevice as sd
import numpy as np
import fire
import img_processor as processor
from img_processor import MetaData


PLAYER_MGR = Playerctl.PlayerManager()
IMAGE_PATH = '/tmp/music_bg.png'
TESTING_IMG_NAME = 'testing.png'

MODE_KEYS = ['sblur', 'bgblur', 'lgrad', 'rgrad']

SELECTED_MODE = MODE_KEYS[0]

def load_track_image_to_metadata(meta: MetaData):
    '''Searches for image for current track in web sources'''

    # if metadata already contains image - we are in a testing mode, no actions needed
    if meta.image_bytes is not None:
        return

    if meta.artUrl is not None:
        print("Started loading...")
        response = requests.get(meta.artUrl)
        if not response.ok:
            restore_bg()
            print("Cannot download from google.")
            return
        print("Downloaded image from google.")
        meta.image_bytes = io.BytesIO(response.content)
        return
    print("Searching in musicbrainz")
    try:
        releases = musicbrainzngs.search_releases(
            f'{meta.artist} - {meta.album}')
        if releases.get('release-count') == -1:
            print("No releases found.")
            restore_bg()
        release_id = releases.get('release-list')[-1].get('id')
        image = musicbrainzngs.get_image(release_id, 'front', 499)
        print("Got image from musicbrainz")
        meta.image_bytes = io.BytesIO(image)
    except Exception as e:
        print(f"Can't get image from musicbrainz. Beacuse : {e}")
    return


def update_bg(meta: MetaData):
    '''Updates desktop background'''

    if meta.image_bytes is None:
        restore_bg()
    try:
        WIDTH = 0
        HEIGHT = 0
        # Calling for monitor sizes here to avoid errors with runtime monitor connection
        for monitor in screeninfo.get_monitors():
            if monitor.height >= HEIGHT and monitor.width >= WIDTH:
                WIDTH = monitor.width
                HEIGHT = monitor.height
        print(f"Biggest screen size is {WIDTH}x{HEIGHT}")

        # Calling for image processing procedure
        # TODO handle here concrete type of image effect
        if SELECTED_MODE == MODE_KEYS[0]:
            processed_image = processor.circle_and_blur(meta, WIDTH, HEIGHT)
        elif SELECTED_MODE == MODE_KEYS[1]:
            processed_image = processor.predefined_image_with_album_in_circle(meta, WIDTH, HEIGHT)
        elif SELECTED_MODE == MODE_KEYS[2]:
            processed_image = processor.linear_gradient_with_circle(meta, WIDTH, HEIGHT)
        elif SELECTED_MODE == MODE_KEYS[3]:
            processed_image = processor.radial_gradient_with_circle(meta, WIDTH, HEIGHT)

        processed_image.save(IMAGE_PATH)
        subprocess.Popen(['feh', '--bg-center', IMAGE_PATH],
                         stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)
    except Exception as e:
        print(f"We're fucked up, sir. Exception: {e}")
        restore_bg()


def restore_bg():
    '''Restores background from Nitrogen'''

    try:
        subprocess.Popen(["nitrogen", "--restore"],
                         stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE)
        #  stream.close()
    except Exception as e:
        print(f"Exception found: {e}")


def on_play(player, status, manager):
    meta = MetaData(player.print_metadata_prop("xesam:artist"),
                    player.print_metadata_prop("xesam:album"),
                    player.print_metadata_prop("mpris:artUrl"))
    load_track_image_to_metadata(meta)
    update_bg(meta)


def on_pause(player, status, manager):
    restore_bg()


def on_metadata_loaded(player, metadata, manager):
    meta = MetaData(player.print_metadata_prop("xesam:artist"),
                    player.print_metadata_prop("xesam:album"),
                    player.print_metadata_prop("mpris:artUrl"))
    load_track_image_to_metadata(meta)
    update_bg(meta)


def init_player(name):
    # choose if you want to manage the player based on the name
    # TODO: exclude mpv, vlc, mp.
    player = Playerctl.Player.new_from_name(name)
    player.connect('playback-status::playing', on_play, PLAYER_MGR)
    player.connect('playback-status::paused', on_pause, PLAYER_MGR)
    player.connect('playback-status::stopped', on_pause, PLAYER_MGR)
    player.connect('metadata', on_metadata_loaded, PLAYER_MGR)
    PLAYER_MGR.manage_player(player)


def on_name_appeared(manager, name):
    init_player(name)


def on_player_vanished(manager, player):
    restore_bg()


def test_image_creation():
    '''Testing of image processing with local file'''

    bytes = []
    with open(TESTING_IMG_NAME, "rb") as image:
        f = image.read()
        bytes = bytearray(f)

    meta = MetaData(image_bytes=bytes)
    update_bg(meta)
    input()
    restore_bg()


def prod_run():
    '''Production run with player manager'''

    PLAYER_MGR.connect('name-appeared', on_name_appeared)
    PLAYER_MGR.connect('player-vanished', on_player_vanished)

    for name in PLAYER_MGR.props.player_names:
        init_player(name)

    main = GLib.MainLoop()
    main.run()


def parse_args(test=False, mode=None):
    '''Swithing between production environement and local image testing'''

    if mode is not None and mode in MODE_KEYS:
        global SELECTED_MODE 
        SELECTED_MODE = mode

    if (test):
        test_image_creation()
    else:
        prod_run()


if __name__ == "__main__":
    musicbrainzngs.set_useragent('Background changer', '0.2.1',
                                 'https://github.com/s3rius')

    fire.Fire(parse_args)
