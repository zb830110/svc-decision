import ah_db
from logging import getLogger
from services.infrastructure.utility import endpoint
from requests import get
import json
import ah_config


def get_express_status(user_id, context_id):
    log = getLogger('ah.expressstatus')
    d = {'ContextId': context_id, 'UserId': user_id,
         'ServiceName': '',
         'Ip': '', 'Event': context_id}

    log.info('Express CM status request sent ', extra=d)

    try:
        headers = {'X-call-context-id': context_id}
        try:
            response = get(f'http://{endpoint()}/express/api/internal/User/{user_id}/status',
                           headers=headers, timeout=(3.05, 20))
        except:
            log.exception("Calling express endpoint failed. Try again.", extra=d)
            response = get(f'http://{endpoint()}/express/api/internal/User/{user_id}/status',
                           headers=headers, timeout=(3.05, 20))
        response = response.json()
    except:
        log.exception("Calling express endpoint error", extra=d)
        return

    return response


def get_express_direct_deposit(user_id, context_id):
    log = getLogger('ah.expressDirectDeposit')
    d = {'ContextId': context_id, 'UserId': user_id,
         'ServiceName': '',
         'Ip': '', 'Event': context_id}

    log.info('Express CM Direct Deposit status request sent ', extra=d)

    try:
        headers = {'X-call-context-id': context_id}
        endpoint = ah_config.get('endpoint.python.url')
        virtual_account = ah_config.get('endpoint.python.virtual_accounts_base')
        request = 'most-recent-direct-deposit'
        endpoint_str = f'http://{endpoint}{virtual_account}{user_id}/{request}'
        try:
            response = get(endpoint_str, headers=headers, timeout=(3.05, 20))
        except:
            log.exception("Calling express endpoint failed. Try again.", extra=d)
            response = get(endpoint_str, headers=headers, timeout=(3.05, 20))
        try:
            response = response.json()
        except:
            response = {}
            log.info('Express CM but does not have Direct Deposit, so return None', extra=d)
    except:
        log.exception("Calling express endpoint error", extra=d)
        return {}

    return response