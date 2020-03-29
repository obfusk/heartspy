<!-- {{{1 -->

    File        : README.md
    Maintainer  : Felix C. Stegerman <flx@obfusk.net>
    Date        : 2020-03-29

    Copyright   : Copyright (C) 2020  Felix C. Stegerman
    Version     : v0.0.1
    License     : AGPLv3+

<!-- }}}1 -->

<!-- TODO: badges -->

[![AGPLv3+](https://img.shields.io/badge/license-AGPLv3+-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

## Description

heartspy - beware of the black queen

Heartspy is a web-based version of the card game "Hearts" (dutch:
"Hartenjagen") for 3 or 4 players.

## Installing

Just `git clone` :)

## Requirements

Python (>= 3.5) & Flask.

### Debian

```bash
$ apt install python3-flask
```

### pip

```bash
$ pip3 install --user Flask   # for Debian; on other OS's you may need
                              # pip instead of pip3 and/or no --user
```

## Running

### Flask

```bash
$ FLASK_APP=hearts.py flask run
```

### Gunicorn

```bash
$ gunicorn hearts:app
```

### Heroku

Just `git push` :)

NB: you'll need to set `WEB_CONCURRENCY=1` b/c it only works
single-theaded atm!

### Password

```bash
$ export HEARTSPY_PASSWORD=swordfish
```

### Forcing HTTPS

```bash
$ export HEARTSPY_HTTPS=force
```

## License

© Felix C. Stegerman

[![AGPLv3+](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.html)

<!-- vim: set tw=70 sw=2 sts=2 et fdm=marker : -->
