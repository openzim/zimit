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

Then, the only thing you need is an HTTP client to tell the proxy to download
a package. So you can go with your browser at
http://localhost:6543/blog.notmyidea.org

And it will download it at the location specified in the configuration file.
