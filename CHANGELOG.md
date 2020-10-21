# Changelog

## 20.14

* New endpoint for queue statistics:

  * `GET /queues/statistics`
  * `GET /queues/<queue_id>/statistics`

## 20.08

* Deprecate SSL configuration

## 20.06

* `GET /cdr`, `GET /users/me/cdr` and `GET /users/<user_uuid>/cdr` return new fields:

  * `requested_name`

## 19.09

* New query parameters have been added to the `GET /users/me/cdr` endpoint:

  * `user_uuid`

## 18.12

* New endpoint for giving internal status of wazo-call-logd:

  * `GET /status`


## 18.07

* Endpoint `GET /cdr`, parameter `limit`: defaults to 1000


## 18.05

* `GET /cdr`, `GET /users/me/cdr` and `GET /users/<user_uuid>/cdr` return new fields:

  * `source_internal_extension`
  * `source_internal_context`
  * `requested_internal_extension`
  * `requested_internal_context`
  * `destination_internal_extension`
  * `destination_internal_context`


## 18.02

* `GET /cdr`, `GET /users/me/cdr` and `GET /users/<user_uuid>/cdr` return new fields:

  * `requested_extension`
  * `requested_context`
  * `destination_user_uuid`
  * `destination_line_id`
  * `source_user_uuid`
  * `source_line_id`


## 17.12

* `GET /cdr`, `GET /users/me/cdr` and `GET /users/<user_uuid>/cdr` accepts new query string
  argument:

  * `from_id`


## 17.11

* New endpoint for getting a single call log:

  * `GET /cdr/<cdr_id>`


## 17.09

* All CDR endpoints can return CSV data, provided a header `Accept: text/csv; charset=utf-8`.
* The default value of query string `direction` has been changed from `asc` to `desc`.


## 17.08

* `GET /users/me/cdr` and `GET /users/<user_uuid>/cdr` accept new query string arguments:

  * `call_direction`
  * `number`

* `GET /cdr` accepts new query string arguments:

  * `call_direction`
  * `number`
  * `user_uuid`
  * `tags`

* `GET /cdr` has new attribute:

  * `id`
  * `answer`
  * `call_direction`
  * `tags`


## 17.07

* New endpoints for listing call logs:

  * `GET /users/<user_uuid>/cdr`
  * `GET /users/me/cdr`

## 17.06

* Call logs objects now have a new attribute `end`
* `GET /cdr` has new parameters:

  * `from`
  * `until`
  * `order`
  * `direction`
  * `limit`
  * `offset`

* `GET /cdr` has new attributes:

  * `total`
  * `filtered`

## 17.05

* New endpoint for listing call logs:

  * `GET /cdr`

## 17.04

* Creation of the HTTP daemon
