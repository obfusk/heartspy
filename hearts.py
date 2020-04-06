#!/usr/bin/python3
# encoding: utf-8

# --                                                            ; {{{1
#
# File        : hearts.py
# Maintainer  : Felix C. Stegerman <flx@obfusk.net>
# Date        : 2020-04-06
#
# Copyright   : Copyright (C) 2020  Felix C. Stegerman
# Version     : v0.0.1
# License     : AGPLv3+
#
# --                                                            ; }}}1

# NB: only works single-threaded!

# TODO:
# * better game over handling
# * better error messages
# * use websocket instead of polling

import itertools, json, os, random, secrets

from collections import OrderedDict as odict

from flask import Flask, redirect, request, render_template, url_for

from obfusk.webgames.common import *

# === logic ===

SUITS, VALUES = "♠♥♣♦", "23456789XJQKA"
WHAT  = dict(X = "10", J = "Jack", Q = "Queen", K = "King", A = "Ace")
CARDS = {
  3 : [ s+v for s in SUITS for v in VALUES[4 if s == "♣" else 5:] ],
  4 : [ s+v for s in SUITS for v in VALUES ]
}
FIRST = { 3: "♣6", 4: "♣2" }
QUEEN = 7

def random_hands(n):
  cards = CARDS[n].copy(); h = len(cards) // n
  random.shuffle(cards)
  return tuple(map(set, itertools.zip_longest(*([iter(cards)] * h))))

def colour(card):
  return "black" if card[0] in "♠♣" else "red"

def is_point(card):
  return card == "♠Q" or card[0] == "♥"

def points_for(card, n):
  if not is_point(card): return 0
  return QUEEN if card == "♠Q" else 1

def distribute_points(players, tricks):
  pts = { p: 0 for p in players }
  now = { p: sum( points_for(c, len(players)) for t in ts for c in t )
             for p, ts in tricks.items() }
  tot = sum(now.values())
  ful = [ p for p, v in now.items() if v == tot ]
  if ful:
    for p in players:
      if p not in ful: pts[p] += tot
  else:
    for p, n in now.items(): pts[p] += n
  return pts

def valid_card(cur, name, card):
  first = not cur["tricks"]
  hand  = cur["cards"][name]
  fst   = FIRST[len(cur["players"])]
  fc    = next(iter(cur["trick"].values()), None)
  if first and card != fst and fst in hand:
    return False  # must start w/ fst
  if first and is_point(card) and any( not is_point(c) for c in hand ):
    return False  # no point @ start
  if fc and card[0] != fc[0] and any( c[0] == fc[0] for c in hand ):
    return False  # follow suit
  return True

def trick_winner(trick):
  it      = iter(trick.items())
  wp, wc  = next(it)
  for p, c in it:
    if c[0] == wc[0] and VALUES.index(c[1]) > VALUES.index(wc[1]):
      wp, wc = p, c
  return wp

def next_player(cur, name):
  p = cur["players"]
  return p[(p.index(name) + 1) % len(p)]

def init_game(game, name):
  if game not in games:
    games[game] = dict(
      players = [], points = {}, cards = {}, tricks = {}, turn = None,
      trick = None, prev_trick = None, msg = None, tick = 0
    )
  cur = current_game(game)
  if name not in cur["players"]:
    if cur["turn"]: raise InProgress()    # in progress -> can't join
    return dict(players = cur["players"] + [name],
                points = { **cur["points"], name: 0 })
  return None

def leave_game(game, name):
  cur = current_game(game)
  if cur["turn"]: raise InProgress()      # in progress -> can't leave
  players = [ p for p in cur["players"] if p != name ]
  return dict(players = players)

def start_round(cur):
  p = cur["players"]
  if len(p) not in [3, 4]: raise InvalidAction("#players must be 3 or 4")
  cards = dict(zip(p, random_hands(len(p))))
  turn  = [ x for x in p if FIRST[len(p)] in cards[x] ][0]
  return dict(cards = cards, tricks = {}, turn = turn,
              trick = odict(), prev_trick = None, msg = None)

def play_card(cur, name, card):
  if name != cur["turn"]: raise InvalidAction("not your turn")
  if name in cur["trick"]: raise InvalidAction("already answered")
  if not valid_card(cur, name, card):
    raise InvalidAction("invalid card")
  hand = cur["cards"][name]
  if card not in hand: raise InvalidAction("card not in hand")
  trick = cur["trick"].copy(); trick[name] = card
  cards = { **cur["cards"], name: hand - set([card]) }
  if len(trick) == len(cur["players"]): # trick done
    win     = trick_winner(trick)
    wtricks = cur["tricks"].get(win, []) + [tuple(trick.values())]
    tricks  = { **cur["tricks"], win: wtricks }
    if len(hand) == 1: # last trick
      points = cur["points"].copy()
      pts = distribute_points(cur["players"], tricks)
      msg = "Points: " + ", ".join( "{} ({})".format(p, n)
                                    for p, n in sorted(pts.items()) )
      for p, n in pts.items(): points[p] += n
      return dict(
        points = points, cards = {}, tricks = {}, turn = None,
        trick = None, prev_trick = trick, msg = msg
      )
    else:
      return dict(cards = cards, tricks = tricks, turn = win,
                  trick = odict(), prev_trick = trick)
  else:
    return dict(cards = cards, turn = next_player(cur, name),
                trick = trick)

def player_data(cur):
  return ", ".join( p + ("*" if cur["turn"] == p else "")
                      + " (" + str(cur["points"][p]) + ")"
                      for p in sorted(cur["players"]) )

def data(cur, game, name):
  what  = lambda c: c[0] + " " + WHAT.get(c[1], c[1])
  ssort = lambda x: sorted(x, key = lambda c: (SUITS.index(c[0]),
                                              VALUES.index(c[1])))
  return dict(
    cur = cur, game = game, name = name, players = player_data(cur),
    colour = colour, msg = cur["msg"],
    valid_card = lambda c: valid_card(cur, name, c),
    trick_winner = trick_winner, what = what, ssort = ssort,
    first = FIRST.get(len(cur["players"])),
    config = json.dumps(dict(game = game, tick = cur["tick"],
                             POLL = POLL))
  )

def game_over(cur, game, name):
  return render_template(
    "done.html", game = game, name = name, players = player_data(cur)
  )

# === http ===

app = define_common_flask_stuff(Flask(__name__), "heartspy")

@app.route("/")
def r_index():
  args = request.args
  game = args.get("game") or secrets.token_hex(10)
  return render_template(
    "index.html", game = game, name = args.get("name"),
    join = "join" in args
  )

@app.route("/play", methods = ["POST"])
def r_play():
  form          = request.form
  game, name    = form.get("game")  , form.get("name")
  action, card  = form.get("action"), form.get("card")
  try:
    if not valid_ident(game): raise InvalidParam("game")
    if not valid_ident(name): raise InvalidParam("name")
    if action in "leave restart rejoin".split():
      if action == "leave":
        update_game(game, leave_game(game, name))
      elif action == "restart":
        restart_game(game)
      return redirect(url_for(
        "r_index", join = "yes" if action != "restart" else None,
        game = game, name = name
      ))
    new = init_game(game, name)
    if new: update_game(game, new)
    cur = current_game(game)
    if action == "start" and cur["turn"] is None:
      update_game(game, start_round(cur))
    elif card:
      update_game(game, play_card(cur, name, card))
    return render_template("play.html", **data(cur, game, name))
  except InProgress:
    return render_template("late.html", game = game)
  except Oops as e:
    return render_template("error.html", error = e.msg()), 400

# vim: set tw=70 sw=2 sts=2 et fdm=marker :
