"""Abstractions for writing Belay servers for AppEngine."""

import logging
import os

from google.appengine.ext import db
from google.appengine.ext import webapp
from django.utils import simplejson as json


def this_server_url_prefix():
  server_name = os.environ['SERVER_NAME']
  server_port = int(os.environ['SERVER_PORT'])
  prefix = 'http://' # TODO(mzero): need to detect if using https
  prefix += server_name
  if server_port != 80: # TODO(mzero): different port if using https
    prefix += ":%d" % server_port
  return prefix
  
  
class BelayException(Exception):
  pass
  

def xhr_response(response):
  response.headers.add_header("Access-Control-Allow-Origin", "*")


def xhr_content(content, content_type, response):
  xhr_response(response)
  response.out.write(content)
  response.headers.add_header("Cache-Control", "no-cache")
  response.headers.add_header("Content-Type", content_type)
  response.headers.add_header("Expires", "Fri, 01 Jan 1990 00:00:00 GMT")


class BcapHandler(webapp.RequestHandler):  
  
  def bcapRequest(self):
      return json.loads(self.request.body)['value']
      
  def bcapResponse(self, jsonResp):
    resp = json.dumps({ 'value': jsonResp })
    xhr_content(resp, "text/plain;charset=UTF-8", self.response)

  def bcapNullResponse(self):
    xhr_response(self.response)
    
  # allows cross-domain requests  
  def options(self):
    m = self.request.headers["Access-Control-Request-Method"]
    h = self.request.headers["Access-Control-Request-Headers"]

    self.response.headers["Access-Control-Allow-Origin"] = "*"
    self.response.headers["Access-Control-Max-Age"] = "2592000"
    self.response.headers["Access-Control-Allow-Methods"] = m      
    if h:
      self.response.headers["Access-Control-Allow-Headers"] = h
    else:
      pass


# Base class for handlers that process capability invocations.
class CapHandler(BcapHandler):

  def set_entity(self, entity):
    self.__entity__ = entity

  def get_entity(self):
    return self.__entity__


class Grant(db.Model):
  internal_path = db.StringProperty() # internal URL passed to the cap handler
  db_entity = db.ReferenceProperty() # reference to DB item passed to cap handler


# A WSGIApplication handler that invokes granted capabilities.
class ProxyHandler(BcapHandler):

  default_prefix = '/caps/'
  prefix_strip_length = len(default_prefix)
  
  __url_mapping__ = None
  
  @classmethod
  def setUrlMap(klass, url_mapping):
    if klass.__url_mapping__ is not None: # do not reinit (FastCGI)
      return
    
    klass.__url_mapping__ = { }
    for (url, handler_class) in url_mapping:
      if hasattr(handler_class, 'default_internal_url'):
        pass
      else:
        handler_class.default_internal_url = url
      klass.__url_mapping__[url] = handler_class

  def __init__(self):
    pass

  def init_cap_handler(self):
    # Strip the '/caps/' prefix off self.request.path
    grant_key_str = self.request.path_info[self.__class__.prefix_strip_length:]

    grant = Grant.get(db.Key(grant_key_str))
    if grant is None:
      # TODO(arjun): appropriate error in response
      raise BelayException('%s, %s' % (self.request.path_info, grant_key_str))
      return None

    handler_class = self.__url_mapping__[grant.internal_path]
    # instantiates appropriate subclass of db.Model
    item = grant.db_entity 

    handler = handler_class()
    handler.set_entity(item)

    self.request.path_info = grant.internal_path # handler sees private path
    handler.initialize(self.request, self.response)
    return handler

  def get(self):
    handler = self.init_cap_handler()
    if handler is None:
      pass
    else:
      handler.get()

  def post(self):
    handler = self.init_cap_handler()
    if handler is None:
      pass
    else:
      handler.post()

  def put(self):
    handler = self.init_cap_handler()
    if handler is None:
      pass
    else:
      handler.put()

  def delete(self):
    handler = self.init_cap_handler()
    if handler is None:
      pass
    else:
      handler.delete()



def get_path(path_or_handler):
  if isinstance(path_or_handler, str):
    return path_or_handler
  elif issubclass(path_or_handler, CapHandler):
    return path_or_handler.default_internal_url
  else:
    raise BelayException('CapServer:get_path::expected string or CapHandler')
     

def grant(path_or_handler, entity):
  path = get_path(path_or_handler)
  item = Grant(internal_path=path, db_entity=entity.key())
  item.put()
  ser_cap = ProxyHandler.default_prefix + str(item.key())
  return ser_cap

def regrant(path_or_handler, entity):
  path = get_path(path_or_handler)
  q = Grant.all()
  q.filter("internal_path = ", path)
  q.filter("db_entity = ", entity)
  items = q.fetch(1)
  if(len(items) > 1):
    raise BelayException('CapServer:regrant::ambiguous internal_path in regrant')
  
  if len(items) == 1:
    return ProxyHandler.default_prefix + str(items[0].key())
  else:
    return grant(path_or_handler, entity)


def set_handlers(cap_prefix, path_map):
  if not cap_prefix.startswith('/'):
    cap_prefix = '/' + cap_prefix
  if not cap_prefix.endswith('/'):
    cap_prefix += '/'
  
  ProxyHandler.prefix_strip_length = len(cap_prefix)
  ProxyHandler.default_prefix = this_server_url_prefix() + cap_prefix
  ProxyHandler.setUrlMap(path_map)