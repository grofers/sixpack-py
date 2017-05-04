import re
import requests
from uuid import uuid4

SIXPACK_HOST = 'http://localhost:5000'
SIXPACK_TIMEOUT = 0.01

# valid experiment_names must be lowercase, start with an alphanumeric and
# contain alphanumerics, dashes and underscores
VALID_EXPT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-_ ]*$")

# Valid alternative and kpi names
VALID_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-_ ]*$", re.I)


def generate_client_id():
    return uuid4()


class Session(object):

    def __init__(self, client_id=None, options=None, params=None):
        use_options = {
            'host': SIXPACK_HOST,
            'timeout': SIXPACK_TIMEOUT
        }

        use_params = {
            'user_agent': None,
            'ip_address': None,
        }

        if options:
            use_options.update(options)

        if params:
            use_params.update(params)

        self.host = use_options['host']
        self.timeout = use_options['timeout']

        self.user_agent = use_params['user_agent']
        self.ip_address = use_params['ip_address']

        if client_id is None:
            self.client_id = generate_client_id()
        else:
            self.client_id = client_id

    def participate(self, api_key, experiment_name, alternatives, force=None, traffic_fraction=1, prefetch=False):
        if VALID_EXPT_NAME_RE.match(experiment_name) is None:
            raise ValueError('Bad experiment name')

        if len(alternatives) < 2:
            raise ValueError('Must specify at least 2 alternatives')

        for alt in alternatives:
            if VALID_NAME_RE.match(alt) is None:
                raise ValueError('Bad alternative name: {0}'.format(alt))

        params = {
            'client_id': self.client_id,
            'api_key': api_key,
            'experiment': experiment_name,
            'alternatives': alternatives,
            'prefetch': prefetch
        }

        if force is not None and force in alternatives:
            params['force'] = force

        if float(traffic_fraction) < 0 or float(traffic_fraction) > 1:
            raise ValueError('Bad traffic_fraction specified (should be a number between 0 and 1')
        params['traffic_fraction'] = str(traffic_fraction)

        response = self.get_response('/participate', params)
        if response['status'] == 'failed':
            response['alternative'] = {'name': alternatives[0]}
        return response

    def convert(self, api_key, experiment_name, kpi=None):
        if VALID_EXPT_NAME_RE.match(experiment_name) is None:
            raise ValueError('Bad experiment name')

        params = {
            'api_key': api_key,
            'experiment': experiment_name,
            'client_id': self.client_id
        }

        if kpi:
            if VALID_NAME_RE.match(kpi) is None:
                raise ValueError('Bad KPI name: {0}'.format(kpi))
            params['kpi'] = kpi

        return self.get_response('/convert', params)

    def build_params(self, params=None):

        if self.ip_address is not None:
            params['ip_address'] = self.ip_address
        if self.user_agent is not None:
            params['user_agent'] = self.user_agent

        return params

    def get_response(self, endpoint=None, params=None):
        url = "{0}{1}".format(self.host, endpoint)

        if params is not None:
            params = self.build_params(params)

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
        except Exception:
            return {"status": "failed", "response": "http error: sixpack is unreachable"}

        if response.status_code != 200:
            return {"status": "failed", "response": response.content}

        try:
            return response.json()
        except ValueError:
            return {"status": "failed", "response": response.content}
