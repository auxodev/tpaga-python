import urllib
import warnings
import sys
from requests.compat import basestring

from tpaga import api_requestor, error, util, upload_api_base

def convert_to_tpaga_object(resp, api_key, account):
    types = {
        'customer': Customer,
    }

    if isinstance(resp, list):
        return [convert_to_tpaga_object(i, api_key, account) for i in resp]
    elif isinstance(resp, dict) and not isinstance(resp, TPagaObject):
        resp = resp.copy()
        klass_name = resp.get('object')
        if isinstance(klass_name, basestring):
            klass = types.get(klass_name, TPagaObject)
        else:
            klass = TPagaObject
        return klass.construct_from(resp, api_key, stripe_account=account)
    else:
        return resp

def populate_headers(idempotency_key):
    if idempotency_key is not None:
        return {"Idempotency-Key": idempotency_key}
    return None

def _compute_diff(current, previous):
    if isinstance(current, dict):
        previous = previous or {}
        diff = current.copy()
        for key in set(previous.keys()) - set(diff.keys()):
            diff[key] = ""
        return diff
    return current if current is not None else ""

def _serialize_list(array, previous):
    array = array or []
    previous = previous or []
    params = {}

    for i, v in enumerate(array):
        previous_item = previous[i] if len(previous) > i else None
        if hasattr(v, 'serialize'):
            params[str(i)] = v.serialize(previous_item)
        else:
            params[str(i)] = _compute_diff(v, previous_item)

    return params


class TPagaObject(dict):
    def __init__(self, id=None, api_key=None, tpaga_account=None, **params):
        super(TPagaObject, self).__init__()

        self._unsaved_values = set()
        self._transient_values = set()

        self._retrieve_params = params
        self._previous = None

        object.__setattr__(self, 'api_key', api_key)
        object.__setattr__(self, 'stripe_account', tpaga_account)

        if id:
            self['id'] = id

    def update(self, update_dict):
        for k in update_dict:
            self._unsaved_values.add(k)

        return super(TPagaObject, self).update(update_dict)

    def __setattr__(self, k, v):
        if k[0] == '_' or k in self.__dict__:
            return super(TPagaObject, self).__setattr__(k, v)
        else:
            self[k] = v

    def __getattr__(self, k):
        if k[0] == '_':
            raise AttributeError(k)

        try:
            return self[k]
        except KeyError as err:
            raise AttributeError(*err.args)

    def __setitem__(self, k, v):
        if v == "":
            raise ValueError(
                "You cannot set %s to an empty string. "
                "We interpret empty strings as None in requests."
                "You may set %s.%s = None to delete the property" % (
                    k, str(self), k))

        super(TPagaObject, self).__setitem__(k, v)

        # Allows for unpickling in Python 3.x
        if not hasattr(self, '_unsaved_values'):
            self._unsaved_values = set()

        self._unsaved_values.add(k)

    def __getitem__(self, k):
        try:
            return super(TPagaObject, self).__getitem__(k)
        except KeyError as err:
            if k in self._transient_values:
                raise KeyError(
                    "%r.  HINT: The %r attribute was set in the past."
                    "It was then wiped when refreshing the object with "
                    "the result returned by Stripe's API, probably as a "
                    "result of a save().  The attributes currently "
                    "available on this object are: %s" %
                    (k, k, ', '.join(self.keys())))
            else:
                raise err

    def __delitem__(self, k):
        raise TypeError(
            "You cannot delete attributes on a StripeObject. "
            "To unset a property, set it to None.")

    @classmethod
    def construct_from(cls, values, key, stripe_account=None):
        instance = cls(values.get('id'), api_key=key,
                       stripe_account=stripe_account)
        instance.refresh_from(values, api_key=key,
                              stripe_account=stripe_account)
        return instance

    def refresh_from(self, values, api_key=None, partial=False,
                     stripe_account=None):
        self.api_key = api_key or getattr(values, 'api_key', None)
        self.stripe_account = \
            stripe_account or getattr(values, 'stripe_account', None)

        # Wipe old state before setting new.  This is useful for e.g.
        # updating a customer, where there is no persistent card
        # parameter.  Mark those values which don't persist as transient
        if partial:
            self._unsaved_values = (self._unsaved_values - set(values))
        else:
            removed = set(self.keys()) - set(values)
            self._transient_values = self._transient_values | removed
            self._unsaved_values = set()
            self.clear()

        self._transient_values = self._transient_values - set(values)

        for k, v in values.iteritems():
            super(TPagaObject, self).__setitem__(
                k, convert_to_tpaga_object(v, api_key, stripe_account))

        self._previous = values

    @classmethod
    def api_base(cls):
        return None

    def request(self, method, url, params=None, headers=None):
        if params is None:
            params = self._retrieve_params
        requestor = api_requestor.APIRequestor(
            key=self.api_key, api_base=self.api_base(),
            account=self.stripe_account)
        response, api_key = requestor.request(method, url, params, headers)

        return convert_to_tpaga_object(response, api_key, self.stripe_account)

    def __repr__(self):
        ident_parts = [type(self).__name__]

        if isinstance(self.get('object'), basestring):
            ident_parts.append(self.get('object'))

        if isinstance(self.get('id'), basestring):
            ident_parts.append('id=%s' % (self.get('id'),))

        unicode_repr = '<%s at %s> JSON: %s' % (
            ' '.join(ident_parts), hex(id(self)), str(self))

        if sys.version_info[0] < 3:
            return unicode_repr.encode('utf-8')
        else:
            return unicode_repr

    def __str__(self):
        return util.json.dumps(self, sort_keys=True, indent=2)

    def to_dict(self):
        warnings.warn(
            'The `to_dict` method is deprecated and will be removed in '
            'version 2.0 of the Stripe bindings. The StripeObject is '
            'itself now a subclass of `dict`.',
            DeprecationWarning)

        return dict(self)

    @property
    def stripe_id(self):
        return self.id

    def serialize(self, previous):
        params = {}
        unsaved_keys = self._unsaved_values or set()
        previous = previous or self._previous or {}

        for k, v in self.items():
            if k == 'id' or (isinstance(k, str) and k.startswith('_')):
                continue
            elif isinstance(v, APIResource):
                continue
            elif hasattr(v, 'serialize'):
                params[k] = v.serialize(previous.get(k, None))
            elif k in unsaved_keys:
                params[k] = _compute_diff(v, previous.get(k, None))
            elif k == 'additional_owners' and v is not None:
                params[k] = _serialize_list(v, previous.get(k, None))

        return params

class TPagaObjectEncoder(util.json.JSONEncoder):

    def __init__(self, *args, **kwargs):
        warnings.warn(
            '`StripeObjectEncoder` is deprecated and will be removed in '
            'version 2.0 of the Stripe bindings.  StripeObject is now a '
            'subclass of `dict` and is handled natively by the built-in '
            'json library.',
            DeprecationWarning)
        super(TPagaObjectEncoder, self).__init__(*args, **kwargs)

class APIResource(TPagaObject):

    @classmethod
    def retrieve(cls, id, api_key=None, **params):
        instance = cls(id, api_key, **params)
        instance.refresh()
        return instance

    def refresh(self):
        self.refresh_from(self.request('get', self.instance_url()))
        return self

    @classmethod
    def class_name(cls):
        if cls == APIResource:
            raise NotImplementedError(
                'APIResource is an abstract class.  You should perform '
                'actions on its subclasses (e.g. Charge, Customer)')
        return str(urllib.quote_plus(cls.__name__.lower()))

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%ss" % (cls_name,)

    def instance_url(self):
        id = self.get('id')
        if not id:
            raise error.InvalidRequestError(
                'Could not determine which URL to request: %s instance '
                'has invalid ID: %r' % (type(self).__name__, id), 'id')
        id = util.utf8(id)
        base = self.class_url()
        extn = urllib.quote_plus(id)
        return "%s/%s" % (base, extn)

class ListObject(TPagaObject):

    def all(self, **params):
        return self.request('get', self['url'], params)

    def create(self, idempotency_key=None, **params):
        headers = populate_headers(idempotency_key)
        return self.request('post', self['url'], params, headers)

    def retrieve(self, id, **params):
        base = self.get('url')
        id = util.utf8(id)
        extn = urllib.quote_plus(id)
        url = "%s/%s" % (base, extn)

        return self.request('get', url, params)


class SingletonAPIResource(APIResource):

    @classmethod
    def retrieve(cls, **params):
        return super(SingletonAPIResource, cls).retrieve(None, **params)

    @classmethod
    def class_url(cls):
        cls_name = cls.class_name()
        return "/v1/%s" % (cls_name,)

    def instance_url(self):
        return self.class_url()


class ListableAPIResource(APIResource):

    @classmethod
    def all(cls, api_key=None, idempotency_key=None,
            tpaga_account=None, **params):
        requestor = api_requestor.APIRequestor(api_key, account=tpaga_account)
        url = cls.class_url()
        response, api_key = requestor.request('get', url, params)
        return convert_to_tpaga_object(response, api_key, tpaga_account)


class CreateableAPIResource(APIResource):

    @classmethod
    def create(cls, api_key=None, idempotency_key=None,
               tpaga_account=None, **params):
        requestor = api_requestor.APIRequestor(api_key, account=tpaga_account)
        url = cls.class_url()
        headers = populate_headers(idempotency_key)
        response, api_key = requestor.request('post', url, params, headers)
        return convert_to_tpaga_object(response, api_key, tpaga_account)


class UpdateableAPIResource(APIResource):

    def save(self, idempotency_key=None):
        updated_params = self.serialize(None)
        headers = populate_headers(idempotency_key)

        if updated_params:
            self.refresh_from(self.request('post', self.instance_url(),
                                           updated_params, headers))
        else:
            util.logger.debug("Trying to save already saved object %r", self)
        return self

class DeletableAPIResource(APIResource):

    def delete(self, **params):
        self.refresh_from(self.request('delete', self.instance_url(), params))
        return self


#resourcePathGet = '/customer/{id}' GET
#resourcePathCreate = '/customer' POST
#resourcePath = '/customer/{id}' DELETE
class Customer(CreateableAPIResource, ListableAPIResource, DeletableAPIResource):
    pass
