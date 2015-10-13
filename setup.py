# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "swagger_client"
VERSION = "1.0.0"



# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = ["urllib3 >= 1.10", "six >= 1.9", "certifi", "python-dateutil"]

setup(
    name=NAME,
    version=VERSION,
    description="TPaga API",
    author_email="sortiz@tpaga.co",
    url="https://tpaga.co/support",
    keywords=["TPaga API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    include_package_data=True,
    long_description="""\
    TPaga Payment Gateway API\n\n[Learn about TPaga](https://tpaga.co)\n\n TPaga uses an REST API with the following workflow\n  1. create an user and obtain a `api_key`. For testing purposes you can use the API key token `d13fr8n7vhvkuch3lq2ds5qhjnd2pdd2` in the [sandbox environment](https://sandbox.tpaga.co/).\n    \n  2. Create `Customer`, there are no obligatory fields, but if you can fill all the fields its highly recommended.\n\n  3. Add payment method to a `Customer`, this API currently supports `CreditCard` and `DaviPlata`\n\n  4. Make a `Charge` to the payment method associated to the `Customer`
    """
)


