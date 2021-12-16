pyproject-install
=================

Command-line Python wheel installer utilising
`installer <https://github.com/pradyunsg/installer>`__.

Usage
-----

    $ pyproject-install --help
    usage: pyproject-install [-h] [--version] [--interpreter INTERPRETER] [--prefix PREFIX] wheel

    Python wheel installer for the masses

    positional arguments:
      wheel                 wheel file to install

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      --interpreter INTERPRETER
                            path of Python interpreter; defaults to running interpreter
      --prefix PREFIX       custom installation prefix
