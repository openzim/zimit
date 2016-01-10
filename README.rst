#####################################
Create ZIM files out of HTTP websites
#####################################

Given any WebSite, get a ZIM file out of it!


How to use it?
##############

Install it using pip
::

  $ pip install zimit

Then, run it how you want, for instance with pserve::

  $ pserve zimit.ini


In a separate process, you also need to run the worker::

  $ rqworker


To test it::

  $ http POST http://0.0.0.0:6543/website url="https://refugeeinfo.eu/" title="Refugee Info" email="alexis@notmyidea.org"



Ubuntu dependencies
###################

You will need to install the following packages:

- zimwriterfs
- httrack

Installing the dependencies
===========================

::

    sudo apt-get install httrack libzim-dev libmagic-dev liblzma-dev libz-dev build-essential

Installing zimwriterfs
======================

::

    git clone https://github.com/wikimedia/openzim.git
    cd openzim/zimwriterfs
    ./autogen.sh
    ./configure
    make

Then upgrade the path to zimwriterfs executable in zimit.ini

::

  $ rqworker & pserve zimit.ini

That's it!
