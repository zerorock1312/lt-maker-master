import glob

from app.editor.data_editor import DB
from app.engine import engine, driver, game_state

import logging

def test_play():
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        game = game_state.start_game()
        driver.run(game)
    except Exception as e:
        logging.error("Engine crashed with a fatal error!")
        logging.exception(e)
        engine.terminate(True)

def test_play_current(level_nid):
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        game = game_state.start_level(level_nid)
        driver.run(game)
    except Exception as e:
        logging.error("Engine crashed with a fatal error!")
        logging.exception(e)
        # For some reason this line is REQUIRED to close the window
        engine.terminate(True)

def get_saved_games():
    GAME_NID = str(DB.constants.value('game_nid'))
    return glob.glob('saves/' + GAME_NID + '-preload-*-*.p')


def test_play_load(level_nid, save_loc=None):
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        if save_loc:
            game = game_state.load_level(level_nid, save_loc)
        else:
            game = game_state.start_level(level_nid)
        driver.run(game)
    except Exception as e:
        logging.error("Engine crashed with a fatal error!")
        logging.exception(e)
        engine.terminate(True)
