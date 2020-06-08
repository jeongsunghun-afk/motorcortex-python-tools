BUILD PIP PACKAGES

To update the repository on PiPy:
1. Tag the version in GIT:
```
git tag -a 1.3.4 -m "version 1.3.4"
```
2. Set the correct version tag in setup.py
3. build 
```
python3 ./setup.py sdist bdist_wheel
```
4. upload
```
python3 -m twine upload dist/motorcortex-python-tools-1.3.3.tar.gz --verbose
```


INSTALL

ON LINUX:
1. "sudo apt install python3 python3-matplotlib python3-jinja2"
2. "sudo pip3 install motorcortex-python"
3. extract the motorcortex-python-tools archive
   "cd motorcortex-python-tools/"
   "sudo python3 ./setup.py install"

ON OTHER SYSTEMS (using PIP)
1. install Python 3.x (see http://www.python.org)
2. use pip3 to install all required packages:
   "pip3 install matplotlib jinja2 motorcortex-python"
3. extract the motorcortex-python-tools archive
   "cd motorcortex-python-tools/"
   execute "python3 ./setup.py install"

   
For instructions:
mcx-datalogger --help
mcx-dataplot --help


