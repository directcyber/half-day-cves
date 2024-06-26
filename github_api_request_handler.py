import requests
import time    
    
def get(url, token):
    head={'Authorization':f'token {token}'}
    response = requests.get(url, headers=head)
    
    # check if we reached our rate limit
    if 'x-ratelimit-remaining' in response.headers and int(response.headers['x-ratelimit-remaining'])==0:
        _sleep_until_reset(int(response.headers['x-ratelimit-reset']))
        return get(url, token)
    
    return response
    
    
def _sleep_until_reset(reset_time):
    gh_api_reset_time = int(reset_time - time.time()) + 120
    print('sleeping ' + str(gh_api_reset_time) + ' seconds')
    time.sleep(gh_api_reset_time)
    
