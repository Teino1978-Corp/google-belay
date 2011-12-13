# Copyright 2011 Google Inc. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/usr/bin/env python

#import json # TODO(mzero): add back for Python27
import os
import sys

from django.utils import simplejson as json # TODO(mzero): remove for Python27

def server_url(path):
  server_name = os.environ['SERVER_NAME']
  server_port = int(os.environ['SERVER_PORT'])
  
  prefix = 'http://'
  default_port = 80
  if os.environ.get('HTTPS', 'off') == 'on':
    prefix = 'https://'
    default_port = 443
    
  prefix += server_name
  if server_port != default_port:
    prefix += ":%d" % server_port
    
  return prefix

def xhr_response(content, content_type):
  content_length = len(content)

  print "Access-Control-Allow-Origin: *"
  print "Cache-Control: no-cache"
  print "Content-Type:", content_type
  print "Content-Length:", content_length
  print "Expires: Fri, 01 Jan 1990 00:00:00 GMT"
  print ""

  sys.stdout.write(content)
  
def bcap_response(response):
  xhr_response(json.dumps({ 'value': response }), "application/json")
