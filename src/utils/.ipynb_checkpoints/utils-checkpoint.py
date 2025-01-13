import os
import sys
from datetime import datetime
import json
import uuid
from flask import Response
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from werkzeug.utils import secure_filename

from src.utils.log import Logger

log = Logger(__name__)

"""
Definition of common function was use in code
"""

def error(msg, status=404):
    res = {
        'message': msg
    }
    return Response(json.dumps(res), status=status, mimetype='application/json')

def ok(data, status=200):
    res = {
        'message': data
    }
    return Response(json.dumps(res), status=status, mimetype='application/json')


def id_generator(size=10):
    return uuid.uuid1().hex[:size]


def save_file(file, folder_path:str):
    """
    Save a file received from a request to the specified folder path.

    Params:
        file: The file object received from the request form.
        folder_path (str): The path to the folder where the file will be saved on the server.

    Returns:
        str or None: The path where the file was saved if successful, None otherwise.

    Note:
        If the content type of the file is not 'application/pdf', logs a warning message
        indicating the failure to save the file due to an incorrect file format.
    """
    file_name = secure_filename(file.filename)

    # create folder if not exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # save file
    save_path = os.path.join(folder_path, file_name)

    if file.content_type != 'application/pdf':
        log.warning_log(f"Failed to save file {file_name}: {file_name[-4:]} instead of .pdf")
        return None
    
    try:
        file.save(save_path)
        return save_path

    except Exception as e:
        log.warning_log(f"Failed to save file {file_name}: {e}")
        return None


def pdf_validation(path:str):
    """
    Validate if a file at the given path is a PDF.

    Params:
        path (str): The path to the file.

    Returns:
        bool: True if the file is a valid PDF, False otherwise.

    Note:
        If the path is None, returns False.
        Checks the content of the file to verify if it is a PDF. If the file is not a PDF,
        logs a warning message indicating the failure to save the file and the reason.
    """
    if path is None: return False
    file_name = path.split("/")[-1]
    
    # check content of file (in case people just change file extension)
    try:
        PdfReader(path)
        return True
    
    except PdfReadError as e:
        log.warning_log(f"Failed to save file {file_name}: Not really  PDF - {e}")
        return False
    
    # other cases
    # your code here

def get_file_modification(path:str) -> str:
    """
    Get the last modification time of a file.

    Params:
        path (str): The path to the file.

    Returns:
        str: A string representing the time of last modification of the file in timestamp format.
             If the file does not exist, returns the current time in the same format.
    """

    if not os.path.exists(path):
        log.warning_log(f"File {path} was deleted before get time modification")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    # file modification timestamp of a file
    m_time = os.path.getmtime(path)

    # convert timestamp into DateTime object
    dt_m = datetime.fromtimestamp(m_time).strftime('%Y-%m-%d %H:%M:%S.%f')
    return dt_m


def action_after_process_file(file_path:str, folder="delete"):
    """
    Delete or save file to reload when somethign wrong

    File should be saved in ./data/upload|reload to use this function
    
    Params::
        file_path (str): path to file need to process
        folder (str): folder to move file to 
    """
    if file_path is None: return False
    file_name = file_path.split("/")[-1]

    if folder == "delete":
        # delete file
        os.remove(file_path) if os.path.exists(file_path) else None

    else:
        # when server cannot connect to DB, move file to reload folder and process later
        os.rename(file_path, file_path.replace("upload", folder))
        log.warning_log(f"Save file {file_name} to {folder} folder")