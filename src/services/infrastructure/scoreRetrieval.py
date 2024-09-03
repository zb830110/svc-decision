import ah_db
import json
from datetime import datetime
from logging import getLogger
from services.infrastructure.utility import endpoint, risk_base
from requests import get


# the same as [risk].[UserModel]
model_id_mapping = {'activation': 2,
                    'max_adjustment': 3,
                    'new_user': 4,
                    'restore': 7,
                    'chime_new_user': 19}


def get_score(user_id, context_id, model_name):
    log = getLogger('ah.ScoreRetrival')
    d = {'ContextId': context_id, 'UserId': user_id,
         'ServiceName': model_name + '-decision-scoreRetrieval',
         'Ip': '', 'Event': context_id}
    time_thresh = 10  # 10 mins
    model_id = model_id_mapping[model_name]

    updated_on, result = read_recent_score(user_id, model_id)
    if updated_on is None:
        log.info('updatedOn was empty', extra=d)
        result = get_API(user_id, context_id, model_name)
        save_recent_score(user_id, model_id, result)
    else:
        time_diff_mins = (datetime.utcnow() - updated_on).total_seconds()/60
        log.info('Number of minutes since updatedOn is %f', time_diff_mins, extra=d)
        if time_diff_mins > time_thresh:
            result = get_API(user_id, context_id, model_name)
            update_recent_score(user_id, model_id, result)
    return result


def get_API(user_id, context_id, model_name):
    log = getLogger('ah.ScoreRetrival')
    d = {'ContextId': context_id, 'UserId': user_id,
         'ServiceName': model_name + '-decision-scoreRetrieval',
         'Ip': '', 'Event': context_id}

    endpoint_str = f'http://{endpoint()}{risk_base()}{model_name}/{user_id}'

    log.info('Risk score requested', extra=d)

    try:
        headers = {'X-call-context-id': context_id}
        try:
            response = get(endpoint_str, headers=headers, timeout=(3.05, 15))
        except:
            log.exception("Calling svc-risk Failed. Try again.", extra=d)
            response = get(endpoint_str, headers=headers, timeout=(3.05, 15))
        response = response.json()
    except:
        log.exception("Calling Risk API error", extra=d)
        return

    return response


def risk_score_result_obj_reader(user_id, model_name):
    model_id = model_id_mapping[model_name]
    result = read_recent_score(user_id, model_id)
    return result


def read_recent_score(user_id, model_id):
    sql = f'''
            SELECT ModelResultObject, UpdatedOn
            FROM DataScience.RiskModelObject
            WHERE ModelId = {model_id} AND UserId = {user_id}
            --    AND DATEDIFF(minute, UpdatedOn, GETDATE()) <= 10
            '''

    with ah_db.open_db_connection('datascience') as connection:
        row = connection.execute(sql).fetchone()

    result = None, None
    if row is not None and len(row) > 0:
        return row[1], json.loads(row[0])
    return result


def save_recent_score(user_id, model_id, result):
    sql = f'''
            INSERT INTO DataScience.RiskModelObject
            (ModelId, UserId, ModelResultObject, Score, CreatedOn, UpdatedOn)
            VALUES ({model_id}, {user_id}, '{json.dumps(result)}', {float(result["score"])}, 
            '{datetime.utcnow()}', '{datetime.utcnow()}')
          '''

    with ah_db.open_db_connection('datascience') as connection:
        connection.execute(sql)

    return


def update_recent_score(user_id, model_id, result):
    sql = f'''
            UPDATE DataScience.RiskModelObject
            SET ModelResultObject='{json.dumps(result)}', Score={float(result["score"])}, UpdatedOn='{datetime.utcnow()}'
            WHERE ModelId={model_id} AND UserId = {user_id}
          '''

    with ah_db.open_db_connection('datascience') as connection:
        connection.execute(sql)

    return
