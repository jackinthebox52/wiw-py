import requests
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

WIW_DEBUG = False

class HTTPSession:
    '''
    This class represents and maintains a session with the undocumented WhenIWork API at https://api.wheniwork.com.
    It handles the login process and stores the session cookie for future requests. It provides methods to query the /swaps, /shifts, and /requests endpoints.
    It can write the session cookie to a local file and read it back in on next instantiation.
    :param location (optional): The location id to restrict queries to. If None, queries will not be restricted.
    :type location: str
    '''
    LOGGED = False
    LOCATION = None #Location id to restrict queries #TODO: Implement location restriction

    def __init__(self, location: str=None, login_details: list=None):
        '''
        Initializes a new session with the WhenIWork API.
        :param location: The location id to restrict queries to. If None, queries will not be restricted.
        :type location: str
        :param login_details: A list containing the email and password to use for login. If None, login details will be read from environment variables.
        :type login_details: list
        '''
        print('Initializing HTTP api session...')
        if login_details is None:
            if 'WIW_EMAIL' in os.environ and 'WIW_PASSWORD' in os.environ:
                self.LOGIN_DETAILS = [os.environ['WIW_EMAIL'], os.environ['WIW_PASSWORD']]
            if self.LOGIN_DETAILS is None:
                raise Exception('Could not find login details. Please set WIW_EMAIL and WIW_PASSWORD environment variables, or supply them to the HTTPSession constructor.')
        else:
            self.LOGIN_DETAILS = login_details
        self.PACKAGE_DATA = _get_package_data_dir()
        self.session = requests.Session()
        if not self.token_login():
            self.credential_login()
            print('Logged in with credentials.')
            self._write_session()
        else:
            print('Logged in with session token.')


    def credential_login(self):
        '''
        Logs into the WhenIWork API and stores the session cookie in the current directory.
        '''
        res = self.session.post('https://api.login.wheniwork.com/login', json={'email': self.LOGIN_DETAILS[0], 'password': self.LOGIN_DETAILS[1]})
        if res.status_code != 200:
            return False
        self.LOGGED = True
        print('Logged in. Setting authorization header...')
        token = res.json()['token']
        self.session.headers.update({'Authorization': token})
        self._write_session()
        return True

    def token_login(self, token: str=None):
        '''
        Logs into the WhenIWork API using the session token stored in the current directory.
        '''
        token = self._read_session()
        if not token:
            return False
        self.session.headers.update({'Authorization': token})#Ensure that the session token is set in the headers. This may not be necessary.
        res = self.session.get('https://login.api.wheniwork.com/people/me')
        if res.status_code != 200:
            return False
        print('Refreshed session token.')
        new_token = res.json()['token']
        self.session.headers.update({'Authorization': new_token})
        self.LOGGED = True
        self._write_session()
        return True

    def list_my_shifts(self):
        '''
        Compiles a list of all shifts that the current user is scheduled for, for the next 365 days, using the /shifts endpoint.
        :return: A list of shifts.
        :rtype: list of dicts (json)
        '''
        id = '46724863'
        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        end_time = (datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        return self.session.get(f'https://api.wheniwork.com/2/shifts?user_id={id}&start={current_time}&end={end_time}').json()

    def list_open_shifts(self):
        '''
        Compiles a list of all shifts for the current user, for the next 365 days, utilizing the /shifts endpoint.
        :return: A dict of shifts.
        :rtype:  dict (json)
        '''
        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        end_time = (datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        url = f'https://api.wheniwork.com/2/shifts?start={current_time}&end={end_time}&include_allopen=true&include_swaps=true&trim_openshifts=false'

        json = self.session.get(url).json()
        for shift in json['shifts']:
            if shift['user_id'] != '0':
                json['shifts'].remove(shift)
        return json

    def list_requests(self):
        '''
        Returns a list of all requests for the current user.
        '''
        return self.session.get('https://api.wheniwork.com/2/requests').json()

    def release_shift(self, shift_id: int=None, shift_ids: list=None):
        '''
        Releases a shift. This calls the /unassign endpoiont with the shift id as a parameter.
        Can take a single shift id or a list of shift ids as input.
        :param shift_id: The id of the shift to release. (Interchangable with shift_ids)
        :type shift_id: int
        :param shift_ids: A list of shift ids to release. (Interchangable with shift_id)
        :type shift_ids: list
        :return: The response from the API.
        :rtype: dict (json)
        '''
        original_headers = self.session.headers
        if (shift_id is None and shift_ids is None) or (shift_id is not None and shift_ids is not None):
            raise Exception('Must provide either shift_id or shift, but not both.')
        id_list = []
        if shift_id is None:
            id_list = shift_ids
        elif shift_ids is None:
            id_list = [shift_id]
        headers = {'Content-type': 'application/json'}
        self.session.headers.update(headers)
        data=json.dumps({'shift_ids': id_list})
        res = self.session.post(f'https://api.wheniwork.com/2/shifts/unassign', data)
        print(res.json())
        self.session.headers = original_headers
        if 'shifts' not in res.json():
            print(f'Failed to release shift {shift_id}.')
            res = False
        return res

    def take_shift(self, shift_id: int=None):
        '''
        Take a shift. This calls the /take endpoint with the shift id as a parameter.
        '''
        original_headers = self.session.headers
        if shift_id is None:
            raise Exception('Must provide shift_id.')
        headers = {'Content-type': 'application/json'}
        self.session.headers.update(headers)
        res = self.session.post(f'https://api.wheniwork.com/2/shifts/{shift_id}/take')
        print(res.json())
        self.session.headers = original_headers
        if 'shift' not in res.json():
            print(f'Failed to take shift {shift_id}.')
            res = False
        else:
            print(f'Took shift {shift_id}.') #DEBUG
        return res


    def _write_session(self):
        '''
        Writes the session cookie to a local file.
        '''
        with open(self.PACKAGE_DATA / 'sessioncookie', 'w') as f:
            f.write(self.session.headers['Authorization'])

    def _read_session(self):
        '''
        Reads the session cookie from a local file, returns False if the file does not exist, returns the token if it does.
        '''
        try:
            with open(self.PACKAGE_DATA / 'sessioncookie', 'r') as f:
                token = f.read()
                self.session.headers.update({'Authorization': token})
                return token
        except FileNotFoundError:
            return False

    #################END CLASS#####################

def _get_package_data_dir():
    '''
    Locates and returns the path to the package data directory.
    :return: The path to the package data directory.
    :rtype: pathlib.Path
    '''
    expected_path = Path(__file__.split('/wheniwork.py')[0]) / 'package_data'
    if not expected_path.is_dir():
        raise Exception(f'Could not find package data directory. at {expected_path}')
    if not expected_path.is_dir():
        expected_path_2 = Path(os.path.expanduser('~')) / '.wiw-py' / 'package_data'
        if not expected_path_2.is_dir():
            expected_path_2.mkdir(parents=True)
            return expected_path_2
        else:
            return expected_path_2
    return expected_path

def _write_json(data: dict, filename: str):
    '''
    Writes a json object to a file.
    :param data: The json object to write.
    :type data: dict
    :param filename: The name of the file to write to.
    :type filename: str
    '''
    with open(filename, 'w') as f:
        json.dump(data, f)

def _read_json(filename: str):
    '''
    Reads a json object from the specified file in the package data directory.
    :param filename: The name of the file to read from.
    :type filename: str
    :return: The json object.
    :rtype: dict
    '''
    package_data = _get_package_data_dir()
    with open(package_data / filename, 'r') as f:
        return json.load(f)


def main():
    session = HTTPSession()
    shifts = session.list_my_shifts()
    requests = session.list_requests()
    #t = session.take_shift(3188245863)
    #r = session.release_shift(3194516684)
    _write_json(shifts, session.PACKAGE_DATA / 'shifts.json')

if __name__ == "__main__":
    main()

