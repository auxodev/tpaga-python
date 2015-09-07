# Stripe Python bindings
# API docs at http://stripe.com/docs/api
# Authors:
# Patrick Collison <patrick@stripe.com>
# Greg Brockman <gdb@stripe.com>
# Andrew Metcalf <andrew@stripe.com>

# Configuration variables

api_key = None
api_base = 'https://sandbox.tpaga.co/api'
upload_api_base = 'https://uploads.stripe.com'
api_version = None
verify_ssl_certs = False

# Resource
from tpaga.resource import (  # noqa
    Customer,
    )

# Error imports.  Note that we may want to move these out of the root
# namespace in the future and you should prefer to access them via
# the fully qualified `stripe.error` module.

from tpaga.error import (  # noqa
    APIConnectionError,
    APIError,
    AuthenticationError,
    CardError,
    InvalidRequestError,
    TPagaError)

# DEPRECATED: These imports will be moved out of the root stripe namespace
# in version 2.0

from tpaga.version import VERSION  # noqa
from tpaga.api_requestor import APIRequestor  # noqa
from tpaga.resource import (  # noqa
    APIResource,
    CreateableAPIResource,
    DeletableAPIResource,
    ListObject,
    ListableAPIResource,
    SingletonAPIResource,
    TPagaObject,
    TPagaObjectEncoder,
    UpdateableAPIResource,
    convert_to_tpaga_object)
from tpaga.util import json, logger  # noqa
