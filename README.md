Main goal is to have rrdtool available in pypy.
The API is close to the bindings comming with rrdtool itself.
It supports

* python2.6
* python2.7
* python3.2
* python3.3
* pypy2.0

You have to install the rrdtool library before using the bindings: ``apt-get install rrdtool``

Furthermore the 'cffi' library must be present: ``apt-get install libffi-dev``


Changelog
=========

0.1 - Mai 17, 2013
------------------

  Initial release
