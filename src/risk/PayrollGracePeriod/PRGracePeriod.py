import ah_db
from services.infrastructure.utility import get_sql_data
from services.infrastructure.scoreRetrieval import get_score
from services.infrastructure.experiment import UserExperiment


# def get_balance(UserId, conn):

#     sql = '''
#         SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
#         SELECT TOP 1
#         UserId, balance.BfpProvidedBankAccountId,
#         balance.Balance, balance.CreatedOn
#         FROM
#         Sync.BfpProvidedBankAccountBalanceHistory AS balance
#         JOIN
#         Sync.UserProvidedBankAccount AS uba
#         ON
#         balance.BfpProvidedBankAccountId = uba.BfpProvidedBankAccountId
#         JOIN
#         BankFeed.UserProvidedBankConnection AS ubc
#         ON
#         uba.UserProvidedBankConnectionId = ubc.UserProvidedBankConnectionId
#         WHERE
#         UserId = ''' + str(UserId) + '''
#         ORDER BY CreatedOn DESC
#         '''

#     df = get_sql_data(sql, conn)
#     if df.shape[0] == 0:
#         return 0.0
#     else:
#         return df['Balance'].values[0]


def get_api_score(user_id, context_id):
    model_name = 'restore'
    response = get_score(user_id, context_id, model_name)
    return response['score']


def get_last_payroll(user_id):
    sql = f'''
          SELECT PayrollActiveStatusId
          FROM payroll.PayrollActiveStatusTracking
          WHERE UserId = {user_id}
          AND DATEDIFF(CURDATE(), EvaluationDate) < 4
          ORDER BY EvaluationDate DESC
          LIMIT 1'''

    with ah_db.open_db_connection('payroll') as conn:
        df = get_sql_data(sql, conn)
    # In case there is no payroll_status
    if df.shape[0] == 0:
        payroll_status = 3
    else:
        payroll_status = df['PayrollActiveStatusId'].values[0]

    return payroll_status


def grace_period_decision(uid, score, last_payroll_active_status):

    cutoff = 0.01114  # grant 20% with grace period
    result = 0

    if 0 <= score <= cutoff:
        if last_payroll_active_status == 2:
            result = 1
    return result


def get_grace_period(user_id, context_id):
    # balance = get_balance(UserId, conn)
    last_payroll_active_status = get_last_payroll(user_id)
    score = get_api_score(user_id, context_id)

    eid = 15
    exp = UserExperiment()
    user_group = exp.get_user_group(user_id, eid)

    if user_group == 2:
        decision = 0
    elif user_group == 3:
        decision = 1
    else:
        decision = grace_period_decision(user_id, score,
                                         # balance,
                                         last_payroll_active_status)

    output = {'score': score,
              # 'balance': balance,
              'gracePeriod': decision,
              'userId': user_id}

    return output


# if __name__ == "__main__":
#     start = time.clock()
#     print("call PRGracePeriod")
#     # Units Test:
#     # # 1 User's last payroll is active
#     User1= {
#         'uid' : 180118,
#         'score' : 0.01,
#         'balance' : 150
#     }
#     result1 = grace_period_decision(User1['uid'], User1['score'], User1['balance'])
#     print("result1:", result1)
#     elapsed = time.clock() - start
#     print("Time spent for", User1['uid'], "function:", elapsed)
    # assert result1 == 1
    # 2 User's last payroll is not active
    # User2= {
    #     'uid' : 938913,
    #     'score' : 0.01,
    #     'balance' : 150
    # }
    # start = time.clock()
    # result2 = grace_period_decision(User2['uid'], User2['score'], User2['balance'])
    # elapsed = time.clock()
    # elapsed = elapsed - start
    # print("Time spent for", User1['uid'], "function:", elapsed)
    # print("result2:", result2)
    # assert result2 == 0
