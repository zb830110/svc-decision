from services.infrastructure.scoreRetrieval import get_score


def get_activation_risk_score(user_id, context_id):
    model_name = 'activation'
    result = get_score(user_id, context_id, model_name)
    return result


def activation_risk_level(score):
    if 0 <= score <= 1:
        level = 'low'

    # no activation risk queue any more
    # elif score > 0.17 and score <= 1:
    #     level = 'medium'

    elif score > 1 and score < 1:
        level = 'high'

    else:  # score==-1
        level = 'unknown'

    return level


def get_activation_risk_level(uid, score):
    # conn = connect_db(3)

    # Experiment pause on 9/29/2016 per request of Ram/Yasho
    # myExp=UserExperiment(conn)
    # eid=2
    # g=myExp.get_user_group(uid,eid)
    g = 2
    level = activation_risk_level(score)
    # if g==1: level=activation_risk_level_1_1(score)
    # elif g==2: level=activation_risk_level_1_2(score)

    #   whitelist=getWhitelist(conn)
    # if uid in whitelist:
    #       level='low'

    # close_db(conn)

    return level, g


if __name__ == "__main__":
    UserId = 180118
    a = get_activation_risk_score(UserId, 'LocatTest')
