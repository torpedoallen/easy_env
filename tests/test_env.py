# -*- coding: utf-8 -*-

import six

if six.PY2:
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

import pytest
from envparse import ConfigurationError

from oh_my_env.base import Env

env = Env('hydra')


env_vars = dict(
    HYDRA_BLANK='',
    HYDRA_STR='foo',
    HYDRA_INT='42',
    HYDRA_FLOAT='33.3',
    HYDRA_BOOL_TRUE='1',
    HYDRA_BOOL_FALSE='0',
    HYDRA_PROXIED='{{STR}}',
    HYDRA_LIST_STR='foo,bar',
    HYDRA_LIST_STR_WITH_SPACES=' foo,  bar',
    HYDRA_LIST_INT='1,2,3',
    HYDRA_LIST_INT_WITH_SPACES=' 1,  2,3',
    HYDRA_DICT_STR='key1=val1, key2=val2',
    HYDRA_DICT_INT='key1=1, key2=2',
    HYDRA_JSON='{"foo": "bar", "baz": [1, 2, 3]}',
    HYDRA_URL='https://example.com/path?query=1',
)


@pytest.fixture(autouse=True, params=['environ', 'envfile'])
def environ(monkeypatch, request):
    """Setup environment with sample variables."""
    if request.param == 'environ':
        for key, val in env_vars.items():
            monkeypatch.setenv(key, val)
    elif request.param == 'envfile':
        env.read_envfile('tests/envfile')


# Helper function
def assert_type_value(cast, expected, result):
    assert cast == type(result)
    assert expected == result


def test_var_not_present():
    with pytest.raises(ConfigurationError):
        env('NOT_PRESENT')


def test_var_not_present_with_default():
    default_val = 'default val'
    assert default_val, env('NOT_PRESENT', default=default_val)


def test_default_none():
    assert_type_value(type(None), None, env('NOT_PRESENT', default=None))


def test_implicit_nonbuiltin_type():
    with pytest.raises(AttributeError):
        env.foo('FOO')


def test_str():
    expected = str(env_vars['HYDRA_STR'])
    assert_type_value(str, expected, env('STR'))
    assert_type_value(str, expected, env.str('STR'))


def test_int():
    expected = int(env_vars['HYDRA_INT'])
    assert_type_value(int, expected, env('INT', cast=int))
    assert_type_value(int, expected, env.int('INT'))


def test_float():
    expected = float(env_vars['HYDRA_FLOAT'])
    assert_type_value(float, expected, env.float('FLOAT'))


def test_bool():
    assert_type_value(bool, True, env.bool('BOOL_TRUE'))
    assert_type_value(bool, False, env.bool('BOOL_FALSE'))


def test_list():
    list_str = ['foo', 'bar']
    assert_type_value(list, list_str, env('LIST_STR', cast=list))
    assert_type_value(list, list_str, env.list('LIST_STR'))
    assert_type_value(list, list_str, env.list('LIST_STR_WITH_SPACES'))
    list_int = [1, 2, 3]
    assert_type_value(list, list_int, env('LIST_INT', cast=list,
                      subcast=int))
    assert_type_value(list, list_int, env.list('LIST_INT', subcast=int))
    assert_type_value(list, list_int, env.list('LIST_INT_WITH_SPACES',
                      subcast=int))
    assert_type_value(list, [], env.list('BLANK', subcast=int))


def test_dict():
    dict_str = dict(key1='val1', key2='val2')
    assert_type_value(dict, dict_str, env.dict('DICT_STR'))
    assert_type_value(dict, dict_str, env('DICT_STR', cast=dict))
    dict_int = dict(key1=1, key2=2)
    assert_type_value(dict, dict_int, env('DICT_INT', cast=dict,
                      subcast=int))
    assert_type_value(dict, dict_int, env.dict('DICT_INT', subcast=int))
    assert_type_value(dict, {}, env.dict('BLANK'))


def test_json():
    expected = {'foo': 'bar', 'baz': [1, 2, 3]}
    assert_type_value(dict, expected, env.json('JSON'))


def test_url():
    url = urlparse('https://example.com/path?query=1')
    assert_type_value(url.__class__, url, env.url('URL'))


def proxied_value():
    assert_type_value(str, 'bar', env('PROXIED'))


def test_preprocessor():
    assert_type_value(str, 'FOO', env('STR', preprocessor=lambda
                                      v: v.upper()))


def test_postprocessor(monkeypatch):
    """
    Test a postprocessor which turns a redis url into a Django compatible
    cache url.
    """
    redis_url = 'redis://:redispass@127.0.0.1:6379/0'
    monkeypatch.setenv('HYDRA_REDIS_URL', redis_url)
    expected = {'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': '127.0.0.1:6379:0',
                'OPTIONS': {'PASSWORD': 'redispass'}}

    def django_redis(url):
        return {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': '{}:{}:{}'.format(url.hostname, url.port, url.path.strip('/')),
            'OPTIONS': {'PASSWORD': url.password}}

    assert_type_value(dict, expected, env.url('redis_url',
                      postprocessor=django_redis))

