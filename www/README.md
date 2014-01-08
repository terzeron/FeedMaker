FeedMaker management web pages
==============================

The simple web pages written in PHP code.

Requirements
------------
1. jQuery
  1. jquery & jquery-ui

Preparation
-----------
You should customize the following installation directories.

1. install FeedMaker to /home/user/workspace/FeedMaker
1. ln -sf /home/user/workspace/FeedMaker/www /www/dir/fm
  1. fm --> www
1. ln -sf /home/user/workspace/FeedMaker /www/dir/fm/work
  1. work --> FeedMaker

This setup makes the directory specification easy.
You don't need to specify the FeedMaker installation directory in web pages(php), nor the web page installation directory in FeedMaker package.

Usage
-----

Try to open http://yoursite.com/fm

