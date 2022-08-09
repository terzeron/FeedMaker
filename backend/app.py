#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import logging.config
from typing import Dict, Any
import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from feed_manager import FeedManager

app = Flask(__name__, static_folder="../frontend/dist", template_folder="../frontend/dist")
app.config['JSON_AS_ASCII'] = False
app.config.from_object(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# logging.basicConfig(filename='run.log', level=logging.DEBUG)
logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()

feed_manager = FeedManager(app.logger)
feed_manager.scan_all_feeds()


@app.route('/', defaults={'path': ''})
def catch_all(path):
    if app.debug:
        return requests.get(f"http://localhost:8080/{path}").text
    return render_template("index.html")


@app.route("/exec_result", methods=["GET"])
def get_exec_result():
    print(f"/exec_result, {request.method} -> get_exec_result()")
    response_object: Dict[str, Any] = {"status": "success"}
    result, error = feed_manager.get_exec_result()
    if result:
        response_object["exec_result"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/problems/<data_type>", methods=["GET"])
def get_problems(data_type):
    print(f"/problems/{data_type}, {request.method} -> get_problems_{data_type}()")
    response_object: Dict[str, Any] = {"status": "success"}
    error = ""
    if data_type == "progress_info":
        progress_info, error = feed_manager.get_problems_progress_info()
        if progress_info:
            response_object["result"] = progress_info
    elif data_type == "public_feed_info":
        public_feed_info, error = feed_manager.get_problems_public_feed_info()
        if public_feed_info:
            response_object["result"] = public_feed_info
    elif data_type == "html_info":
        html_info, error = feed_manager.get_problems_html_info()
        if html_info:
            response_object["result"] = html_info
    elif data_type == "element_info":
        element_info, error = feed_manager.get_problems_element_info()
        if element_info:
            response_object["result"] = element_info
    elif data_type == "status_info":
        status_info, error = feed_manager.get_problems_status_info()
        if status_info:
            response_object["result"] = status_info

    if "result" not in response_object or not response_object["result"]:
        response_object["message"] = error
        response_object["status"] = "failure"
    return jsonify(response_object)


@app.route("/search/<keyword>", methods=["GET"])
def search(keyword):
    print(f"/search, {request.method} -> search({keyword})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.search(keyword)
    if result or not error:
        response_object["feeds"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/search_site/<keyword>", methods=["GET"])
def search_site(keyword):
    print(f"/search_site, {request.method} -> search_site({keyword})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.search_site(keyword)
    if result or not error:
        response_object["search_result_list"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/public_feeds/<feed_name>", methods=["DELETE"])
def remove_public_feed(feed_name):
    print(f"/public_feeds/{feed_name}, {request.method} -> remove_public_feed({feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    feed_manager.remove_public_feed(feed_name)
    response_object["status"] = "success"
    return jsonify(response_object)


@app.route("/groups/<group_name>/site_config", methods=["GET", "PUT"])
def site_config(group_name):
    print(f"/groups/{group_name}/site_config, {request.method} -> get_site_config({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    if request.method == "GET":
        result, error = feed_manager.get_site_config(group_name)
        if result:
            response_object["configuration"] = result
            print(response_object["configuration"])
            response_object["status"] = "success"
            print(result)
        else:
            response_object["message"] = error
    elif request.method == "PUT":
        print("/groups/{group_name}/site_config, {request.method} -> save_site_config({group_name})")
        post_data = request.get_json()
        print(post_data)
        success_or_fail, error = feed_manager.save_site_config(group_name, post_data)
        if success_or_fail:
            response_object["status"] = "success"
        else:
            response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/toggle", methods=["PUT"])
def toggle_group(group_name):
    print(f"/groups/{group_name}/toggle, {request.method} -> toggle_group({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.toggle_group(group_name)
    if result:
        response_object["status"] = "success"
        response_object["new_name"] = result
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/htmls/<html_file_name>", methods=["DELETE"])
def remove_html_file(group_name, feed_name, html_file_name):
    print(f"/groups/{group_name}/feeds/{feed_name}/htmls/{html_file_name}, {request.method} -> remove_html_file({group_name}, {feed_name}, {html_file_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    feed_manager.remove_html_file(group_name, feed_name, html_file_name)
    response_object["status"] = "success"
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/htmls", methods=["DELETE"])
def remove_html(group_name, feed_name):
    print(f"/groups/{group_name}/feeds/{feed_name}/htmls, {request.method} -> remove_html({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    feed_manager.remove_html(group_name, feed_name)
    response_object["status"] = "success"
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/run", methods=["POST"])
def run(group_name, feed_name):
    print(f"/groups/{group_name}/feeds/{feed_name}/run, {request.method}, {request.get_json()} -> run({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    post_data = request.get_json()
    result, error = feed_manager.run(group_name, feed_name, post_data["alias"])
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/toggle", methods=["PUT"])
def toggle_feed(group_name, feed_name):
    print(f"/groups/{group_name}/feeds/{feed_name}/toggle, {request.method} -> toggle_feed({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.toggle_feed(group_name, feed_name)
    if result:
        response_object["status"] = "success"
        response_object["new_name"] = result
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/list", methods=["DELETE"])
def remove_list(group_name, feed_name):
    print(f"/groups/{group_name}/feeds/{feed_name}/list, {request.method} -> remove_list({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    feed_manager.remove_list(group_name, feed_name)
    response_object["status"] = "success"
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/alias", methods=["GET", "DELETE"])
def get_alias(group_name, feed_name):
    print(f"/groups/{group_name}/feeds/{feed_name}/alias, {request.method} -> get_alias({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    if request.method == "GET":
        result, error = feed_manager.get_alias(group_name, feed_name)
        if result:
            response_object["status"] = "success"
            response_object["alias"] = result
        else:
            response_object["message"] = error
    elif request.method == "DELETE":
        result, error = feed_manager.remove_alias(group_name, feed_name)
        if result:
            response_object["status"] = "success"
            response_object["alias"] = result
        else:
            response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/rename/<new_alias>", methods=["PUT"])
def rename_alias(group_name, feed_name, new_alias):
    print(f"/groups/{group_name}/feeds/{feed_name}/rename/{new_alias}, {request.method} -> rename_alias({group_name}, {feed_name}, {new_alias})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.rename_alias(group_name, feed_name, new_alias)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/check_running", methods=["GET"])
def check_running(group_name, feed_name):
    #print(f"/groups/{group_name}/feeds/{feed_name}/check_running, {request.method} -> check_running({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result = feed_manager.check_running(group_name, feed_name)
    response_object["status"] = "success"
    response_object["running_status"] = result
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>", methods=["DELETE", "POST", "GET"])
def get_feed_info(group_name, feed_name):
    response_object: Dict[str, Any] = {"status": "failure"}
    if request.method == "GET":
        print(f"/groups/{group_name}/feeds/{feed_name}, {request.method} -> get_feed_info({group_name}, {feed_name})")
        feed_info, error = feed_manager.get_feed_info_by_name(group_name, feed_name)
        if feed_info or not error:
            # success in case of feed without configuration
            response_object["feed_info"] = feed_info
            print(response_object["feed_info"])
            response_object["status"] = "success"
        else:
            response_object["message"] = error
    elif request.method == "POST":
        print(f"/groups/{group_name}/feeds/{feed_name}, {request.method} -> save_config_file({group_name}, {feed_name})")
        post_data = request.get_json()
        result, error = feed_manager.save_config_file(group_name, feed_name, post_data)
        if result:
            response_object["status"] = "success"
        else:
            response_object["message"] = error
    elif request.method == "DELETE":
        print(f"/groups/{group_name}/feeds/{feed_name}, {request.method} -> remove_feed({group_name}, {feed_name})")
        result, error = feed_manager.remove_feed(group_name, feed_name)
        if result:
            response_object["status"] = "success"
        else:
            response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds", methods=["GET"])
def get_feeds_by_group(group_name):
    print(f"/groups/{group_name}/feeds, {request.method} -> get_feeds_by_group({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.get_feeds_by_group(group_name)
    if result or not error:
        # success in case of group without any feed
        response_object["feeds"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>", methods=["DELETE"])
def remove_group(group_name):
    print(f"/groups/{group_name}, {request.method} -> remove_group({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.remove_group(group_name)
    if result or not error:
        response_object["feeds"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups", methods=["GET"])
def get_groups():
    print("/groups, {request.method} -> get_groups()")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.get_groups()
    if result:
        response_object["groups"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


if __name__ == "__main__":
    app.run(host="0.0.0.0", threaded=True)
