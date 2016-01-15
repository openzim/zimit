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



Debian dependencies
####################

Installing the dependencies
===========================

::

    sudo apt-get install httrack libzim-dev libmagic-dev liblzma-dev libz-dev build-essential libtool redis-server automake pkg-config

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

How to deploy?
##############

There are multiple ways to deploy such service, so I'll describe how I do it
with my own best-practices.

First of all, get all the dependencies and the code. I like to have everything
available in /home/www, so let's consider this will be the case here::

  $ mkdir /home/www/zimit.notmyidea.org
  $ cd /home/www/zimit.notmyidea.org
  $ git clone https://github.com/almet/zimit.git

Create a virtual environment and activate it::

  $ virtualenv venv
  $ activate venv/bin/activate

Then, you can change the configuration file, by creating a new one::

  $ cd zimit
  $ cp zimit.ini local.ini

From there, you need to update the configuration to point to the correct
binaries and locations.

Nginx configuration
===================

::

  # the upstream component nginx needs to connect to
    upstream zimit_upstream {
        server unix:///tmp/zimit.sock;
    }

    # configuration of the server
    server {
        listen      80;
        listen   [::]:80;
        server_name zimit.ideascube.org;
        charset     utf-8;

        client_max_body_size 200M;

        location /zims {
            alias /home/ideascube/zimit.ideascube.org/zims/;
            autoindex on;
        }

        # Finally, send all non-media requests to the Pyramid server.
        location / {
            uwsgi_pass  zimit_upstream;
            include     /var/ideascube/uwsgi_params;
        }
      }


UWSGI configuration
===================

::

  [uwsgi]
  uid = ideascube
  gid = ideascube
  chdir           = /home/ideascube/zimit.ideascube.org/zimit/
  ini             = /home/ideascube/zimit.ideascube.org/zimit/local.ini
  # the virtualenv (full path)
  home            = /home/ideascube/zimit.ideascube.org/venv/

  # process-related settings
  # master
  master          = true
  # maximum number of worker processes
  processes       = 4
  # the socket (use the full path to be safe
  socket          = /tmp/zimit.sock
  # ... with appropriate permissions - may be needed
  chmod-socket    = 666
  # stats           = /tmp/ideascube.stats.sock
  # clear environment on exit
  vacuum          = true
  plugins         = python


That's it!
