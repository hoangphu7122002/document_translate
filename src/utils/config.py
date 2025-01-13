import configparser
import logging

logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s %(message)s', level=logging.ERROR)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Config(object):
    """Class to read config file
    """

    def __init__(self, config_file='..config/config-dev.ini'):
        self.config = configparser.ConfigParser()
        log.info('Read config file %s', config_file)
        read_ok = self.config.read(config_file)
        if not read_ok:
            msg = 'Cannot read config from %s' % config_file
            log.error(msg)
            raise Exception(msg)

    def get_section(self, section):
        try:
            return self.config[section]
        except KeyError:
            return None

    def get(self, section, key, default=None):
        section = self.get_section(section)
        return section.get(key, default) if section is not None else default

    def getboolean(self, section, key, default=None):
        section = self.get_section(section)
        return section.getboolean(key, default) if section is not None else default

    def getint(self, section, key, default=None):
        section = self.get_section(section)
        return section.getint(key, default) if section is not None else default