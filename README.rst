pyproject-install
=================

Command-line Python wheel installer utilising
`installer <https://github.com/pradyunsg/installer>`__.

Usage
-----

.. code-block::

   $ pyproject-install --help
   usage: pyproject-install [-h] [--verbose] [--version] [--interpreter INTERPRETER]
                            [--prefix PREFIX]
                            wheel

   Python wheel installer for the masses

   positional arguments:
     wheel                 wheel file to install

   optional arguments:
     -h, --help            show this help message and exit
     --verbose             increase verbosity
     --version             show program's version number and exit
     --interpreter INTERPRETER
                           path of Python interpreter; defaults to `which python`
     --prefix PREFIX       custom installation prefix
