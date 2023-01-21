My Notes on Python
==================

In this directory, `requirements.txt` is not the list of requirements
for this project, instead it is my notes on all the Python modules
I find interesting / useful.

Installing Python on Linux
--------------------------

    sudo apt-get install build-essential tk-dev uuid-dev lzma-dev liblzma-dev
    sudo apt-get build-dep python3 idle-python3.11
    
    umask 022
    sudo mkdir -v /opt/python3.11.1
    sudo chown -c `id -u`:`id -g` /opt/python3.11.1
    
    wget https://www.python.org/ftp/python/3.11.1/Python-3.11.1.tar.xz
    tar xJvf Python-3.11.1.tar.xz
    
    cd Python-3.11.1
    ./configure --prefix=/opt/python3.11.1 --enable-optimizations
    make && make test && make install
    
    sudo ln -snfv /opt/python3.11.1 /opt/python3
    
    # in ~/.profile:
    test -d /opt/python3 && PATH="/opt/python3/bin:$PATH"
    
    which python3
    which pip3
    which idle3
    python3 --version
    
    python3 -m pip install --upgrade pip wheel
    # see requirements.txt for how to install those
    
    # to add something to PYTHONPATH in .profile:
    export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$HOME/code/igbdatatools"
    
    # https://docs.python.org/3/download.html
    wget https://docs.python.org/3/archives/python-3.11.1-docs-html.tar.bz2
    tar xjvf python-3.11.1-docs-html.tar.bz2
    mv python-3.11.1-docs-html /opt/python3/html
    find /opt/python3/html -type d -exec chmod 755 '{}' + -o -exec chmod 644 '{}' +

Windows Notes
-------------

During install, I usually choose `autocrlf=input`.

Getting `python3` to reference `python` on Win 10, shown from Git Bash:

    rm "$HOME/AppData/Local/Microsoft/WindowsApps/python3.exe"
    cd "$HOME/AppData/Local/Programs/Python/Python311/"
    cp python.exe python3.exe

In Windows 10, environment variables can be added for the current user via the
Control Panel, in User Accounts you can find a setting "Change my environment
variables", or you can press Windows+R and then enter:

    rundll32.exe sysdm.cpl,EditEnvironmentVariables

To apply execute permissions to files on Windows:

    git ls-files --stage
    git update-index --chmod=+x <filenames>

Python Versions
---------------

Some of the reasons I require the latest Python versions:

- Python 3.10
  - newer typing features like union type operator
  - `zip(..., strict=True)` (`more_itertools.zip_equal` has been deprecated)
- Python 3.11
  - `datetime.fromisoformat` is more flexible (e.g. supports trailing `Z`)
  - `contextlib.chdir`
  - `typing.Self`


Author, Copyright, and License
------------------------------

Copyright (c) 2022 Hauke Daempfling <haukex@zero-g.net>
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, <https://www.igb-berlin.de/>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

