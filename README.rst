Flask-ToyBox
============

Sorry, no documentation yet, this is totally **pre-alpha** quality.

I just needed something to implement somehow RESTful (or, to be precise, what
I consider RESTful) API. I've looked around for a readily available solution,
but didn't found anything that suited my needs and desires. So I've wrote a
hopefully reusable library to do it.

See feature list below for main points about this library.

Features
--------

What's implemented:

- Extensible (de)serialization for both input and output, with HTTP content-type
  negotiation.
- Handling of GET and PATCH requests (object retrieval and modification)
- Relatively flexible field-level permissions. Could be always supplemented by
  TastyPie-like hydration/dehydration methods.
- SQLAlchemy model helpers.

What's missing:

- Examples.
- Documentation. There are some docstrings in source code, but not much.
- POST, PUT and DELETE requests (object creation and deletion).
- Overriding negotiation using query string (i.e. `?format=json`)
- Pagination helpers. Pagination is possible, but you have to do it by hand.
- Nested resources.
- Better test coverage.

Copyright
---------

Copyright (c) 2012, Aleksey Zhukov.

Distributed under MIT (Expat) license. See `LICENSE.txt` for details.
