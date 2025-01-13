import logging
from logging import Formatter
from logging import FileHandler
from datetime import datetime
from dotenv import load_dotenv
import os

dotenv_path = ".env" # Path("home_dir+'/src/api/.env'")
load_dotenv(dotenv_path=dotenv_path)

class Logger():
    """
    A class for logging events.

    Attributes:
        log_path (str): Path to save log files on the server.
        logger (object): Logger object.
        formatter (str): Format used by the logger to save events.
        file_handler (object): Object for saving events to a file.
    """

    def __init__(self, name=__name__):

        # set file name by YYYY_MM_DD to save log by day
        # change it if you NEED
        now = datetime.now() 
        file_name = now.strftime('log_{0}_%Y_%m_%d.log'.format(os.getcwd().split("/")[-1]))

        self.log_path = 'log/'
        # self.logger = logging.getLogger(f'{os.getcwd().split("/")[-1]}')
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # template 
        # change it if you NEED
        self.formatter = Formatter('[%(asctime)s] [%(levelname)5s] - [in %(name)s]: %(message)s')
        print(file_name)
        with open(file_name, 'w') as fp:
            pass
        # file handle
        
        # self.file_handler = FileHandler(self.log_path+file_name)
        self.file_handler = FileHandler(file_name)
        self.logger.addHandler(self.file_handler)
        self.file_handler.setFormatter(self.formatter)


    def info_log(self, message):
        """
        Save an info log.

        Param:
            message (str): The message to be saved to the log file.
        """
        self.clear_handler()
        self.file_handler.setLevel(logging.INFO)
        self.logger.info(message)


    def warning_log(self, message):
        """"
        Save a warning log.

        Param:
            message (str): The message to be saved to the log file.
        """
        self.clear_handler()
        self.file_handler.setLevel(logging.WARNING)
        self.logger.error(message)

    def clear_handler(self):
        """
        Clear the handler to prevent duplicate handlers.
        """
        if (self.logger.hasHandlers()):
            self.logger.handlers.clear()
        self.logger.addHandler(self.file_handler)