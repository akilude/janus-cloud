# -*- coding: utf-8 -*-
import gevent.monkey
gevent.monkey.patch_all()

import sys
from januscloud.sentinel.config import load_conf
from daemon import DaemonContext
import os


_terminated = False


def main():
    if len(sys.argv) == 2:
        config = load_conf(sys.argv[1])
    else:
        config = load_conf('/opt/janus-cloud/conf/janus-sentinel.yml')

    if config['general']['daemonize']:
        with DaemonContext(stdin=sys.stdin,
                           stdout=sys.stdout,
                           # working_directory=os.getcwd(),
                           files_preserve=list(range(3, 100))):
            do_main(config)
    else:
        do_main(config)


def do_main(config):

    import signal
    import shlex
    from gevent.pywsgi import WSGIServer
    from pyramid.config import Configurator
    from pyramid.renderers import JSON
    from januscloud.common.utils import CustomJSONEncoder
    from januscloud.common.logger import set_root_logger
    from januscloud.sentinel.process_mngr import ProcWatcher
    from januscloud.sentinel.janus_server import JanusServer
    from januscloud.sentinel.poster_manager import add_poster
    from januscloud.sentinel.poster.http_poster import HttpPoster

    set_root_logger(**(config['log']))

    import logging
    log = logging.getLogger(__name__)

    janus_watcher = None
    try:
        # set up janus server
        janus_server = JanusServer(
            server_name=config['janus']['server_name'],
            server_ip=config['janus']['server_ip'],
            ws_port=config['janus']['ws_port'],
            admin_ws_port=config['janus']['admin_ws_port'],
            pingpong_interval=config['janus']['pingpong_interval'],
            statistic_interval=config['janus']['statistic_interval'],
            request_timeout=config['janus']['request_timeout'],
            hwm_threshold=config['janus']['hwm_threshold'],
            admin_secret=config['janus']['admin_secret']
        )

        # set up janus_watcher
        if config['proc_watcher']['cmdline']:
            janus_watcher = ProcWatcher(args=shlex.split(config['proc_watcher']['cmdline']),
                                        error_restart_interval=config['proc_watcher']['error_restart_interval'],
                                        poll_interval=config['proc_watcher']['poll_interval'],
                                        process_status_cb=janus_server.on_process_status_change)

        for poster_params in config['posters']:
            add_poster(janus_server, **poster_params)

        # rest api config
        pyramid_config = Configurator()
        pyramid_config.add_renderer(None, JSON(indent=4, check_circular=True, cls=CustomJSONEncoder))
        pyramid_config.include('januscloud.sentinel.rest')
        # TODO register service to pyramid registry
        pyramid_config.registry.janus_server = janus_server
        pyramid_config.registry.janus_watcher = janus_watcher

        # start admin rest api server
        rest_server = WSGIServer(
            config['admin_api']['http_listen'],
            pyramid_config.make_wsgi_app(),
            log=logging.getLogger('rest server')
        )

        # start janus watcher
        if janus_watcher:
            janus_watcher.start()

        log.info('Janus Sentinel Started')

        def stop_sentinel():
            log.info('Janus Proxy receives signals to quit...')
            global _terminated
            _terminated = True
            rest_server.stop()

        gevent.signal(signal.SIGTERM, stop_sentinel)
        gevent.signal(signal.SIGQUIT, stop_sentinel)
        gevent.signal(signal.SIGINT, stop_sentinel)

        rest_server.serve_forever()

        # while not _terminated:
        #    gevent.sleep(1)

        # stop janus watcher
        if janus_watcher:
            janus_watcher.destroy()
            janus_watcher = None

        log.info("Janus-sentinel Quit")

    except Exception:
        log.exception('Failed to start Janus Sentinel')
        if janus_watcher:
            janus_watcher.destroy()
            janus_watcher = None


if __name__ == '__main__':
    main()
