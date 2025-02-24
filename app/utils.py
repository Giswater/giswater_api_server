"""
Copyright © 2024 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-

import os
import logging
import json

from datetime import date
from .database import SCHEMA_NAME, get_db, user


app = None
api = None
tenant_handler = None
mail = None

def create_body_dict(project_epsg=None, form={}, feature={}, filter_fields={}, extras={}) -> str:
    info_type = 1
    lang = "es_ES"  # TODO: get from app lang

    client = {
        "device": 5,
        "lang": lang,
        "cur_user": user,
    }
    if info_type is not None:
        client["infoType"] = info_type
    if project_epsg is not None:
        client["epsg"] = project_epsg

    json_str = json.dumps({
        "client": client,
        "form": form,
        "feature": feature,
        "filterFields": filter_fields,
        "pageInfo": {},
        "data": {
            **filter_fields,
            "pageInfo": {},
            **extras
        }
    })
    return f"$${json_str}$$"

def create_response(db_result=None, form_xml=None, status=None, message=None):
    """ Create and return a json response to send to the client """

    response = {"status": "Failed", "message": {}, "version": {}, "body": {}}

    if status is not None:
        if status in (True, "Accepted"):
            response["status"] = "Accepted"
            if message:
                response["message"] = {"level": 3, "text": message}
        else:
            response["status"] = "Failed"
            if message:
                response["message"] = {"level": 2, "text": message}

        return response

    if not db_result and not form_xml:
        response["status"] = "Failed"
        response["message"] = {"level": 2, "text": "DB returned null"}
        return response
    elif form_xml:
        response["status"] = "Accepted"

    if db_result:
        response = db_result
    response["form_xml"] = form_xml

    return response


def execute_procedure(log, function_name, parameters=None, set_role=True, needs_write=False):
    """ Manage execution database function
    :param function_name: Name of function to call (text)
    :param parameters: Parameters for function (json) or (query parameters)
    :param log_sql: Show query in qgis log (bool)
    :param set_role: Set role in database with the current user
    :return: Response of the function executed (json)
    """

    # Manage schema_name and parameters
    schema_name = SCHEMA_NAME
    if schema_name is None:
        log.warning(" Schema is None")
        remove_handlers()
        return create_response(status=False, message="Schema not found")
    sql = f"SELECT {schema_name}.{function_name}("
    if parameters:
        sql += f"{parameters}"
    sql += ");"

    execution_msg = sql
    response_msg = ""

    with get_db() as conn:
        result = dict()
        print(f"SERVER EXECUTION: {sql}\n")
        identity = user
        try:
            with conn.cursor() as cursor:
                if set_role: cursor.execute(f"SET ROLE '{identity}';")
                cursor.execute(sql)
                result = cursor.fetchone()
                result = result[0] if result else None
            response_msg = json.dumps(result)
        except Exception as e:
            result = {"dbmessage": str(e)}
            response_msg = str(e)

        if not result or result.get('status') == "Failed":
            log.warning(f"{execution_msg}|||{response_msg}")
        else:
            log.info(f"{execution_msg}|||{response_msg}")

        if result:
            print(f"SERVER RESPONSE: {json.dumps(result)}\n")

        return result

# Create log pointer
def create_log(class_name):
    today = date.today()
    today = today.strftime("%Y%m%d")

    # Directory where log file is saved, changes location depending on what tenant is used
    # logs_directory = "/var/log/giswater-api-server"
    logs_directory = "logs"
    if not os.path.exists(logs_directory):
        os.makedirs(logs_directory)

    # Check if today's direcotry is created
    today_directory = f"{logs_directory}/{today}"
    if not os.path.exists(today_directory):
        # This shouldn't be necessary, but somehow the directory magically apears
        # (only the first time of the day it is created)
        try:
            os.makedirs(today_directory)
        except FileExistsError:
            print("Directory already exists. wtf")

    service_name = os.getcwd().split(os.sep)[-1]
    # Select file name for the log
    log_file = f"{service_name}_{today}.log"

    fileh = logging.FileHandler(f"{today_directory}/{log_file}", "a", encoding="utf-8")
    # Declares how log info is added to the file
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s:%(name)s:%(message)s", datefmt = "%d/%m/%y %H:%M:%S")
    fileh.setFormatter(formatter)

    # Removes previous handlers on root Logger
    remove_handlers()
    # Gets root Logger and add handler
    logger_name = f"{class_name.split('.')[-1]}"
    log = logging.getLogger(logger_name)
    # log = logging.getLogger()
    log.addHandler(fileh)
    log.setLevel(logging.DEBUG)
    return log

# Removes previous handlers on root Logger
def remove_handlers(log=logging.getLogger()):
    for hdlr in log.handlers[:]:
        log.removeHandler(hdlr)
