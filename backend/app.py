#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import json
from typing import Dict, Any
import logging.config
import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from feed_manager import FeedManager

app = Flask(__name__, static_folder="../frontend/dist", template_folder="./dist")
app.config['JSON_AS_ASCII'] = False
app.config.from_object(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(filename='run.log', level=logging.DEBUG)

feed_manager = FeedManager(app.logger)
feed_manager.load_all_feeds()


@app.route('/', defaults={'path': ''})
def catch_all(path):
    if app.debug:
        return requests.get('http://localhost:8080/{}'.format(path)).text
    return render_template("index.html")


@app.route("/exec_result", methods=["GET"])
def get_exec_result():
    print("/exec_result, %r -> get_exec_result()" % request.method)
    response_object = {"status": "success"}
    result, error = feed_manager.get_exec_result()
    if result:
        response_object["exec_result"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/problems", methods=["GET"])
def get_problems():
    print("/problems, %r -> get_problems()" % request.method)
    response_object = {"status": "success"}
    result, error = feed_manager.get_problems()
    if result:
        response_object["problems"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups", methods=["GET"])
def get_groups():
    print("/groups, %r -> get_groups()" % request.method)
    response_object = {"status": "failure"}
    result, error = feed_manager.get_groups()
    if result:
        response_object["groups"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>", methods=["DELETE"])
def remove_group(group_name):
    print("/groups/<group_name>, %r -> remove_group(%s)" % (request.method, group_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.remove_group(group_name)
    if result or not error:
        response_object["feeds"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds", methods=["GET"])
def get_feeds_by_group(group_name):
    print("/groups/<group_name>/feeds, %r -> get_feeds_by_group(%s)" % (request.method, group_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.get_feeds_by_group(group_name)
    if result or not error:
        # success in case of group without any feed
        response_object["feeds"] = result
        response_object["status"] = "success"
        print(result)
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>", methods=["DELETE", "POST", "GET"])
def get_feed_info(group_name, feed_name):
    response_object = {"status": "failure"}
    if request.method == "GET":
        print("/groups/<group_name>/feeds/<feed_name>, %r -> get_feed_info(%s, %s)" % (request.method, group_name, feed_name))
        result, error = feed_manager.get_feed_info_by_name(feed_name)
        if result or not error:
            # success in case of feed without configuration
            response_object["configuration"] = result
            print(response_object["configuration"])
            response_object["status"] = "success"
        else:
            response_object["message"] = error
    elif request.method == "POST":
        print("/groups/<group_name>/feeds/<feed_name>, %r -> save_config_file(%s, %s)" % (request.method, group_name, feed_name))
        post_data = request.get_json()
        print(post_data)
        result, error = feed_manager.save_config_file(group_name, feed_name, post_data)
        if result:
            response_object["status"] = "success"
        else:
            response_object["message"] = error
    elif request.method == "DELETE":
        print("/groups/<group_name>/feeds/<feed_name>, %r -> remove_feed(%s, %s)" % (request.method, group_name, feed_name))
        result, error = feed_manager.remove_feed(group_name, feed_name)
        if result:
            response_object["status"] = "success"
        else:
            response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/run", methods=["POST"])
def run(group_name, feed_name):
    print("/groups/<group_name>/feeds/<feed_name>/run, %r -> run(%s, %s)" % (request.method, group_name, feed_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.run(group_name, feed_name)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/toggle", methods=["PUT"])
def toggle_group(group_name):
    print("/groups/<group_name>/toggle, %r -> toggle_group(%s)" % (request.method, group_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.toggle_group(group_name)
    if result:
        response_object["status"] = "success"
        response_object["new_name"] = result
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/toggle", methods=["PUT"])
def toggle_feed(group_name, feed_name):
    print("/groups/<group_name>/feeds/<feed_name>/toggle, %r -> toggle_feed(%s, %s)" % (request.method, group_name, feed_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.toggle_feed(group_name, feed_name)
    if result:
        response_object["status"] = "success"
        response_object["new_name"] = result
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/list", methods=["DELETE"])
def remove_list(group_name, feed_name):
    print("/groups/<group_name>/feeds/<feed_name>/list, %r -> remove_list(%s, %s)" % (request.method, group_name, feed_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.remove_list(group_name, feed_name)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/html", methods=["DELETE"])
def remove_html(group_name, feed_name):
    print("/groups/<group_name>/feeds/<feed_name>/html, %r -> remove_html(%s, %s)" % (request.method, group_name, feed_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.remove_html(group_name, feed_name)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/alias", methods=["GET"])
def get_alias(group_name, feed_name):
    print("/groups/<group_name>/feeds/<feed_name>/alias, %r -> get_alias(%s, %s)" % (request.method, group_name, feed_name))
    response_object = {"status": "failure"}
    result, error = feed_manager.get_alias(group_name, feed_name)
    if result:
        response_object["status"] = "success"
        response_object["alias"] = result
    else:
        response_object["message"] = error
    return jsonify(response_object)


@app.route("/groups/<group_name>/feeds/<feed_name>/rename/<new_alias>", methods=["PUT"])
def rename_alias(group_name, feed_name, new_alias):
    print("/groups/<group_name>/feeds/<feed_name>/rename/<new_alias>, %r -> rename_alias(%s, %s, %s)" % (request.method, group_name, feed_name, new_alias))
    response_object = {"status": "failure"}
    result, error = feed_manager.rename_alias(group_name, feed_name, new_alias)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return jsonify(response_object)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
