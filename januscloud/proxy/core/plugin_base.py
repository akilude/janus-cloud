# -*- coding: utf-8 -*-

import logging
from januscloud.common.utils import error_to_janus_msg, create_janus_msg
from januscloud.common.error import JanusCloudError, JANUS_ERROR_UNKNOWN_REQUEST, JANUS_ERROR_INVALID_REQUEST_PATH
from januscloud.common.schema import Schema, Optional, DoNotCare, \
    Use, IntVal, Default, SchemaError, BoolVal, StrRe, ListVal, Or, STRING, \
    FloatVal, AutoDel

log = logging.getLogger(__name__)


class PluginBase(object):
    """ This base class for plugin """

    def init(self, config_path):
        pass

    def get_version(self):
        pass

    def get_version_string(self):
        pass

    def get_description(self):
        pass

    def get_name(self):
        pass

    def get_author(self):
        pass

    def create_handle(self):
        pass

if __name__ == '__main__':
    pass





