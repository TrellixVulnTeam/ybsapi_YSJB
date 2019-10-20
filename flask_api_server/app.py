import os
from base64 import b64encode
from collections import OrderedDict
from hashlib import sha256
from hmac import HMAC
from urllib.parse import urlparse, parse_qsl, urlencode

from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_restplus import Api, Resource, fields
import random
from maps_api.mapsapi import PyMapsAPI
from keyword_extractor.PyMorpho import PyMorpho
from resources import keywords

# TODO save return data to file

client_secret = "krPB9BSIrxRa3qJQwbIQ"
N_RANDOM_WORDS = 5
app = Flask(__name__)
api = Api(app, version='1.0', title='Sample API',
    description='A sample API',
)

cors = CORS(app)
pymorpho = PyMorpho()
mapsapi = PyMapsAPI()

app.config['CORS_HEADERS'] = 'Content-Type'
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from db.models import User


def parse_friends(json_data):
    tmp_friends = []
    friends_in_app = []

    for friend in json_data:
        person = {}
        for key, value in friend.items():
            if key == 'id':
                person[key] = value
            if key == 'first_name':
                person[key] = value
            if key == 'last_name':
                person[key] = value
            if key == 'photo_200':
                person[key] = value

        tmp_friends.append(person)

    for friend in tmp_friends:
        friend_id = str(friend['id'])
        user = User.query.filter_by(user_vk_id=friend_id).first()
        if user:
            friends_in_app.append(friend)

    return friends_in_app


@api.route('/')
@api.doc(params={'healthCheck': ''})
class Hello(Resource):
    def get(self):
        return  {'Yasos Biba Studios': True}

    @api.response(403, 'Not Authorized')
    def post(self, id):
        api.abort(403)




@app.route('/user/communities/<id>', methods=['GET', 'POST'])
@cross_origin()
def get_communities(id):
    referrer = request.headers.get("Referer")
    if referrer:
        if is_vk_user(referrer):
            app.logger.info('User Authorized')
        else:
            app.logger.warning('User Not Authorized')
        data = request.get_json()

        response = []
        for word in pymorpho.format_user_keywords(pymorpho.get_keywords_from_groups(groups=data)):
            place = mapsapi.find_one_place(word)
            if place is not None:
                response.extend(place)

        for word in random.sample(set(keywords.words), N_RANDOM_WORDS):
            place = mapsapi.find_one_place(word)
            if place is not None:
                response.extend(place)

        print(f"Response:{response}")
    return jsonify({'data': response})


@app.route('/user/friends/<id>', methods=['GET', 'POST'])
@cross_origin()
def get_friends(id):
    referrer = request.headers.get("Referer")
    if referrer:
        if is_vk_user(referrer):
            app.logger.info('User Authorized')
        else:
            app.logger.warning('User Not Authorized')
    data = request.get_json()
    result = parse_friends(data)
    return jsonify({'data': result})


@app.route('/user/authorize/<id>', methods=['GET'])
@cross_origin()
def task_info(id):
    users = User.query.filter_by(user_vk_id=id).first()
    app.logger.info(f'User: {users}')
    referrer = request.headers.get("Referer")
    app.logger.info(f'Referer: {referrer}')
    if referrer:
        if is_vk_user(referrer):
            app.logger.info('User Authorized')
        else:
            app.logger.warning('User Not Authorized')
    if users:
        app.logger.info(f"User {users} exists")
        result = {"data": {"vk_user_id": id, "status": "old"}}
        return jsonify(result)
    else:
        try:
            new_user = User(user_vk_id=id)
            db.session.add(new_user)
            db.session.commit()
            app.logger.info(f"User {new_user} created")
            result = {"data": {"vk_user_id": id, "status": "new"}}
            return jsonify(result)
        except Exception as e:
            return (str(e))


def is_vk_user(url) -> bool:
    """Check VK Apps signature"""
    query = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
    vk_subset = OrderedDict(sorted(x for x in query.items() if x[0][:3] == "vk_"))
    hash_code = b64encode(HMAC(client_secret.encode(), urlencode(vk_subset, doseq=True).encode(), sha256).digest())
    decoded_hash_code = hash_code.decode('utf-8')[:-1].replace('+', '-').replace('/', '_')
    return query["sign"] == decoded_hash_code


if __name__ == '__main__':
    app.run()
