import ah_config
import ah_db
import random
import numpy as np
from services.infrastructure.utility import get_sql_data
from logging import getLogger
import traceback
from sqlalchemy import exc


class UserExperiment:
    def __init__(self, conn=None):
        self.conn = conn

    def get_exp_group(self, uid, eid):
        sql = f'''
                 SELECT GroupId
                 FROM DataScience.ExperimentGroup
                 WHERE userid={uid} and experimentid={eid}'''

        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            group = result.fetchall()

        if len(group) > 0:
            return group[0][0]
        else:
            return None

    def get_all_current_ux_experiment(self):
        sql = """
              SELECT ExperimentId
              FROM DataScience.Experiment
              WHERE UXExperiment = 1
              AND CURRENT_TIMESTAMP() BETWEEN StartTime AND EndTime
              """

        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            row = result.fetchall()
        return [x['ExperimentId'] for x in row]

    def get_experiment_date_range(self, eid):
        sql = f"""
              SELECT COUNT(*) AS cntExp
              FROM DataScience.Experiment
              WHERE experimentid={eid}
              AND CURRENT_TIMESTAMP() BETWEEN StartTime AND EndTime
              """

        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            row = result.fetchone()
        return row['cntExp']

    def get_nested_experiment(self, eid):
        sql = f"""
              SELECT NestedExperimentId, GroupIdInNestedExperiment,
              DefaultGroupIdInNestedExperiment
              FROM DataScience.Experiment
              WHERE experimentid={eid}
              """

        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            row = result.fetchone()

        return row['NestedExperimentId'], row['GroupIdInNestedExperiment'], \
               row['DefaultGroupIdInNestedExperiment']

    def get_user_group(self, uid, eid):
        exp_exist = self.get_experiment_date_range(eid)
        if not exp_exist:
            return 1

        nested_exp_id, nested_group_id, def_nested_group_id = \
            self.get_nested_experiment(eid)
        if all([nested_exp_id, nested_group_id, def_nested_group_id]):
            ngid = self.get_user_group(uid, nested_exp_id)
            if ngid == nested_group_id:
                return self.pull_create_user_group(uid, eid)
            else:
                return def_nested_group_id
        else:
            return self.pull_create_user_group(uid, eid)

    def pull_create_user_group(self, uid, eid):
        sql = f'''
              SELECT GroupId
              FROM DataScience.ExperimentGroup
              WHERE userid={uid} and experimentid={eid}
              '''

        result = None
        num_try = 0
        log = getLogger('ah.ExperimentGroup')
        d = {'UserId': uid, 'ServiceName': 'ExperimentGroupAssignment'}

        while result is None and num_try <= 2:
            try:
                num_try += 1
                with ah_db.open_db_connection('datascience') as connection:
                    result = connection.execute(sql)
                    row = result.fetchone()
                if row is not None:
                    result = row['GroupId']
                    return result
                else:
                    result = self.assign_user_group(eid, uid)
                    return result
            except exc.IntegrityError:
                pass
            except:
                log.exception('User experiment group assignment failed', extra=d)
                raise

        if num_try == 3:
            log.exception('Retry of experiment group assignment exceeded 3 times', extra=d)
            raise Exception('Retry of experiment group assignment exceeded 3 times, userid = %s' % uid)

    def get_user_group_for_ux_exp(self, eids, uid):
        if len(eids) == 0:
            return []
        else:
            eids_str = "(" + ",".join([str(x) for x in eids]) + ")"
            sql = '''
                  SELECT eg.ExperimentId, eg.GroupId, egd.GroupDescription
                  FROM DataScience.ExperimentGroup eg
                  JOIN DataScience.ExperimentGroupDescriptions egd
                  ON eg.ExperimentId = egd.ExperimentId AND eg.GroupId = egd.GroupId
                  WHERE eg.userid=%d and eg.experimentid IN %s
                  ''' % (uid, eids_str)

            with ah_db.open_db_connection('datascience') as connection:
                result = connection.execute(sql)
                rows = result.fetchall()

            var = self.get_experiment_variables_for_ux_exp(eids)

            [row.update({'Variables':
                         var[row['ExperimentId']][row['GroupId']]}) for row in rows]
            return rows

    def get_group_users(self, eid, gid):
        sql = f'''
              SELECT UserId
              FROM DataScience.ExperimentGroup
              WHERE ExperimentId = {eid} AND GroupId = {gid}
              '''

        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            rows = result.fetchall()

        uids = [x[0] for x in rows]
        return uids

    def get_batch_groups(self, eid, uids):
        # return group 1 for all users if experiment is not currently active
        if not self.get_experiment_date_range(eid):
            return {'1': uids}

        uids1 = set(uids)

        if len(uids) == 1:
            uids = '(' + str(uids[0]) + ')'
        else:
            uids = tuple(uids)

        sql = f'''
                  SELECT UserId, GroupId
                  FROM DataScience.ExperimentGroup
                  WHERE ExperimentId = {eid} and UserId in {uids}
                  ORDER BY GroupId
                  '''

        with ah_db.open_db_connection('datascience') as connection:
            df = get_sql_data(sql, connection)

        l1 = df.groupby('GroupId')['UserId'].apply(list).to_dict()

        if len(l1) < len(uids):

            uids2 = set(df['UserId'])
            uids3 = uids1 - uids2

            if len(uids3) > 0:
                for uid in uids3:
                    try:
                        self.assign_user_group(eid, uid)
                    except exc.IntegrityError:
                        pass

            with ah_db.open_db_connection('datascience') as connection:
                df = get_sql_data(sql, connection)

            l2 = df.groupby('GroupId')['UserId'].apply(list).to_dict()
            return l2
        else:
            return l1

    def assign_user_group(self, eid, uid):
        splits = self.get_group_split(eid)
        g = int(np.random.choice(range(1, len(splits)+1), p=splits))

        sql = f'''
              INSERT INTO DataScience.ExperimentGroup
              (ExperimentId, UserId, GroupId, CreatedOn)
              VALUES ({eid}, {uid}, {g}, CURRENT_TIMESTAMP)
              '''
        with ah_db.open_db_connection('datascience') as connection:
            connection.execute(sql)
        return g

    @staticmethod
    def mandatory_assign_user_group(eid, uid, group_id):
        sql_query = f'''
                SELECT UserId, GroupId
                FROM DataScience.ExperimentGroup
                WHERE ExperimentId = {eid}
                  AND UserId = {uid}
                '''

        with ah_db.open_db_connection('datascience') as connection:
            df = get_sql_data(sql_query, connection)

        if df.shape[0] == 0:
            sql = f'''
                  INSERT INTO DataScience.ExperimentGroup
                  (ExperimentId, UserId, GroupId, CreatedOn)
                  VALUES ({eid}, {uid}, {group_id}, CURRENT_TIMESTAMP)
                  '''

            with ah_db.open_db_connection('datascience') as connection:
                connection.execute(sql)

    def mandatory_reassign_user_group(self, eid, uid, group_id):
        sql = f'''
              UPDATE DataScience.ExperimentGroup
              SET GroupId = {group_id}
              WHERE experimentid = {eid} AND UserId = {uid}
              '''

        with ah_db.open_db_connection('datascience') as connection:
            connection.execute(sql)

    def get_user_group_from_db(self, eid, uids):
        sql_query = f'''
        SELECT UserId, GroupId
        FROM DataScience.ExperimentGroup
        WHERE ExperimentId = {eid}
          AND UserId in {tuple(uids)}
        '''

        with ah_db.open_db_connection('datascience') as connection:
            df = get_sql_data(sql_query, connection)

        return df

    def get_preassigned_user_group(self, eid, uids):
        if not uids:
            return [{}]

        expt_exists = self.get_experiment_date_range(eid)
        if not expt_exists:
            grps = [{'UserId': uid} for uid in uids]
            return grps

        # Get group assignments
        df = self.get_user_group_from_db(eid, uids)
        grps = df.to_dict(orient='records')

        # If all requested userids are in experiment, return groups
        if len(df) == len(uids):
            return grps

        # Add remaining userids without groups
        assigned_uids = set(df['UserId'])
        for uid in uids:
            if uid not in assigned_uids:
                grps.append({'UserId': uid})

        return grps

    def assign_user_group_for_ux_exp(self, eids, uid):
        gids = []
        ds = []
        for eid in eids:
            try:
                g = self.assign_user_group(eid, uid)
            except:
                g = self.get_user_group(uid, eid)
                log = getLogger('ah.ExperimentGroup')
                log.warning('User experiment group assignment duplicated'
                            '(experimentId = %s)'
                            '(userid = %s)' % (eid, uid))
            gids.append(g)
            desc = self.get_exp_group_descriptions(eid)
            ds.append(desc[g])
        var = self.get_experiment_variables_for_ux_exp(eids)
        return [{'ExperimentId': x[0],
                 'GroupId': x[1],
                 'GroupDescription': x[2],
                 'Variables': var[x[0]][x[1]]} for x in zip(eids, gids, ds)]

    def get_exp_group_descriptions(self, eid):
        sql = f'''
              SELECT GroupId, GroupDescription
              FROM DataScience.ExperimentGroupDescriptions
              WHERE experimentid={eid}
              ORDER BY groupid
              '''

        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            rows = result.fetchall()
        # group id has to be continuous and starting from 1
        return {x['GroupId']: x['GroupDescription'] for x in rows}

    def get_group_split(self, eid):
        sql = f'''
               SELECT split
               FROM DataScience.ExperimentGroupDescriptions
               WHERE experimentid={eid}
               ORDER BY groupid
               '''

        # group id has to be continuous and starting from 1
        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            rows = result.fetchall()

        if len(rows) == 0:
            raise NameError('No Group Split for experiment: {}'.format(eid))
        else:
            return [row['split'] for row in rows]

    def get_experiment_variables(self, eid):
        sql = f'''
              SELECT GroupId, VariableName, VariableValue
              FROM DataScience.UXExperimentVariables
              WHERE experimentid={eid}
              '''

        # group id has to be continuous and starting from 1
        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            rows = result.fetchall()

        group_ids = set([x['GroupId'] for x in rows])
        return {y: {x['VariableName']: x['VariableValue']
                    for x in rows if x['GroupId'] == y} for y in group_ids}

    def get_experiment_variables_for_ux_exp(self, eids):
        var_dict = {}
        for eid in eids:
            exp_vars = self.get_experiment_variables(eid)
            var_dict[eid] = exp_vars
        return var_dict

    def get_all_user_id(self):
        sql = '''
                SELECT distinct f.userid
                from moneymovement.transactions t
                JOIN moneymovement.transactionstofundstransfers ttft
                ON t.TransactionID = ttft.TransactionID
                JOIN moneymovement.FundsTransfers f
                ON ttft.FundsTransferId = f.FundsTransferId
                where  t.TransactionTypeID=3 and t.StatusID in (2,3)
                and f.PostingDate>'2016-01-01'
                order by f.userid
                '''

        try:
            with ah_db.open_db_connection('moneyMovement') as connection:
                result = connection.execute(sql)
                r = result.fetchall()
        except:
            print(traceback.format_exc())
        return [l[0] for l in r]

    @staticmethod
    def get_new_user_id():
        sql = '''
                SELECT DISTINCT UserId
                FROM miscellaneous.Users
                WHERE CreatedOn >= '2017-02-15'
                '''
        try:
            with ah_db.open_db_connection('miscellaneous') as connection:
                result = connection.execute(sql)
                r = result.fetchall()
        except:
            print(traceback.format_exc())
        return [l[0] for l in r]

    def assign_all_user_group(self, eid):
        uids = self.get_all_user_id()
        for uid in uids:
            self.assign_user_group(eid, uid)

    def is_experiment_valid(self, eid):
        sql = f'''
              SELECT (CASE WHEN CURRENT_TIMESTAMP() BETWEEN
                     StartTime AND EndTime THEN 1 ELSE 0 END) AS valid
              FROM DataScience.Experiment
              WHERE ExperimentId = {eid}
              '''

        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            row = result.fetchone()

        #     print( row)
        if len(row) == 0:
            raise NameError('request of experiment group'
                            'assignment failure,'
                            'experiment does not exist'
                            ', experimentid = %s.' % eid)
        else:
            return row['valid']

    def delete_exp_group(self, uid, eid):
        sql = f'''
                 DELETE
                 FROM datascience.ExperimentGroup
                 WHERE UserId={uid}
                 AND experimentid={eid}
              '''

        with ah_db.open_db_connection('datascience') as connection:
            connection.execute(sql)

    def get_user_exp_groups(self, uid):
        # get all groups a user is in for all currently active experiments
        exps = self.get_all_live_exps()
        exps_result = []
        for exp in exps:
            eid = exp['experimentId']
            group = self.get_user_group_from_d_bwith_description(uid, eid)
            if len(group) > 0:
                exps_result.append(group[0])
        return exps_result

    def get_user_group_from_d_bwith_description(self, uid, eid):
        sql = f'''
        SELECT eg.GroupId, egd.groupDescription
        FROM DataScience.ExperimentGroup eg
        JOIN DataScience.ExperimentGroupDescriptions egd
        ON eg.ExperimentId = egd.ExperimentId
        AND eg.GroupId = egd.GroupId
        WHERE userid={uid} and eg.experimentid={eid}
        '''
        return ah_db.execute_to_json('datascience', sql)

    def get_all_live_exps(self):
        sql = '''
        SELECT experimentId, experimentDescription
        FROM datascience.experiment
        WHERE NOW() >= StartTime AND NOW() <= EndTime
        AND Alive = 1
        '''
        return ah_db.execute_to_json('datascience', sql)

    @staticmethod
    def get_user_id_from_email(email):
        sql = f'''
        SELECT userid
        FROM miscellaneous.users
        WHERE UserName = '{email}'
        '''
        user_id = ah_db.execute_to_json('miscellaneous', sql)
        if len(user_id) == 0:
            return {'userid': 'null'}
        return user_id[0]


class TransactionExperiment:
    def __init__(self, conn=None):
        self.conn = conn

    def getUserGroup(self, uid, eid):
        splits = self.get_group_split(eid)
        rolling_sum = 0
        r = random.random()
        g = 1
        for s in splits:
            rolling_sum += s
            if r < rolling_sum:
                break
            g += 1

        return g

    def get_group_split(self, eid):
        sql = f'''
                 select split
                 from DataScience.ExperimentGroupDescriptions
                 where experimentid={eid}
                 order by groupid
                 '''

        # group id has to be continuous and starting from 1
        with ah_db.open_db_connection('datascience') as connection:
            result = connection.execute(sql)
            rows = result.fetchall()
        return [row['split'] for row in rows]


def init_experiment(eid):
    my_exp = UserExperiment()
    my_exp.assign_all_user_group(eid)


def get_user_ids(conn):
    sql = """
        SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED
        select distinct UserId
        from dbo.Activations
        Where HourStatusID not in (8,9,10)
    """
    df = get_sql_data(sql, conn)
    return df


if __name__ == "__main__":

    import ah_db
    import ah_config
    ah_config.initialize()

    """
    with ah_db.open_db_connection('sqlserver') as connection:
        myExp = UserExperiment(conn)
        uid = 547078
        # a = myExp.get_user_group_for_ux_exp([9], 547078)
        b = myExp.get_experiment_variables_for_ux_exp([9, 10])
        a = myExp.get_user_group_for_ux_exp([9, 10], uid)
        # eids = myExp.get_all_current_ux_experiment()
        # # print(myExp.assign_user_group_for_ux_exp(eids, 180198))
        # print(myExp.get_user_group_for_ux_exp(eids, 180198))
        # print(myExp.assign_user_group_for_ux_exp([99], 3))
    """

    """
    eid = 20
    UserId = 420
    exp = UserExperiment()
    print('All current UX experiment')
    print(exp.get_all_current_ux_experiment())
    print('Experiment date range')
    print(exp.get_experiment_date_range(eid))
    print('Nested experiment')
    print(exp.get_nested_experiment(eid))
    print('User group')
    print(exp.get_user_group(UserId, eid))
    print(exp.get_user_group(UserId, 88))
    #print('User group for UX experiment')
    #print(exp.get_user_group_for_ux_exp([eid], UserId))
    print('Group Users')
    print(exp.get_group_users(eid, 1))
    #print('Assignment')
    #exp.assign_user_group(eid, UserId)
    print('Group description')
    print(exp.get_exp_group_descriptions(eid))
    print('Group Split')
    print(exp.get_group_split(eid))
    print('Experiment Variables')
    print(exp.get_experiment_variables(eid))
    print('Experiment is valid')
    print(exp.is_experiment_valid(eid))
    """

    expt = UserExperiment()

    # Test case: Experiment doesn't exist
    print("<<< Test case: Experiment doesn't exist >>>")
    eid = -200
    uids = [-1, -2, -3, -4, 62]
    grps = expt.get_preassigned_user_group(eid, uids)
    print(grps)

    # Test case: User list is empty
    print("<<< Test case: User list is empty >>>")
    eid = 200
    uids = []
    grps = expt.get_preassigned_user_group(eid, uids)
    print(grps)

    # Test case: All users are in experiment
    print("<<< Test case: All users are in experiment >>>")
    eid = 200
    uids = [-1, -2, -3, -4]
    grps = expt.get_preassigned_user_group(eid, uids)
    print(grps)

    # Test case: One or more users not in experiment
    print("<<< Test case: One or more users not in experiment >>>")
    eid = 200
    uids = [-1, -2, -3, -4, -62, -63]
    grps = expt.get_preassigned_user_group(eid, uids)
    print(grps)

    # df = get_user_ids(conn)
    # eid = 20
    # UserId = 420
    # myExp = UserExperiment()
    # group = myExp.get_user_group(UserId, eid)
    # print(group)
