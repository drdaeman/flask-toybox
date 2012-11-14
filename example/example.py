#!/usr/bin/env python

from example import app, db

db.create_all()
app.run(debug=True, port=5001)
