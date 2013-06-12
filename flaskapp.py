# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Base module which sets up the flask app object
"""

import uuid
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

from pyfarm.config.database import DBConfig

app = Flask("PyFarm")
app.config["SQLALCHEMY_DATABASE_URI"] = DBConfig().url("testing")
app.secret_key = str(uuid.uuid4())  # TODO: this needs a config or extern lookup

db = SQLAlchemy(app)