from ah_fastapi_utils.exceptions import ServiceUnavailable, InvalidInput
from datadog import statsd
from datetime import datetime
from ddtrace import tracer
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
import product.sameDayACHRestore.sameDayACHRestore as sdachr
import product.unemployment.existinguser as eu
from pytz import timezone
import risk.maxAdjustment.maxAdjust as ma
import risk.maxAdjustment.maxAdjustCompetitor as mac
import risk.maxAdjustment.RecoverySuccessMaxAdjust as rs
import risk.maxAdjustment.requestMaxAdjustment as rma
import risk.maxAdjustment.resfailMaxAdjust as rm
import risk.maxAdjustment.futureMaxAdjust as fma
import risk.newUser.newUser as nu
import risk.newUser.ChimeNewUser as ch
import risk.PayrollGracePeriod.PRGracePeriod as pgp
import risk.RestoreGracePeriod.RGracePeriod as rgp
import risk.ruleEngine.ruleEngine as re
import risk.savings.depositRequestRisk as drr
from services.infrastructure.experiment import UserExperiment

app = APIRouter()
logger = logging.getLogger("ah.decision")


@app.get("/max-adjustment/{user_id}", operation_id="GetMaxAdjustment")
async def get_max_adjustment(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Max adjustment requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        result_score = ma.get_new_max(user_id, context_id)
        logger.info("Final output for user %d: %s", user_id, result_score, extra=d)

        if 'newmax' in result_score:
            logger.info("Successfully got new max for user %d", user_id, extra=d)
            result = result_score
            result['userId'] = user_id
        else:
            logger.info("Unable to get new max for user %d, old max returned", user_id, extra=d)
            oldmax = ma.get_old_max(user_id)
            boost_amount = ma.get_temp_max(user_id)
            oldmax = max(50, oldmax - boost_amount)
            result = dict()
            result['score'] = -1
            result['tipPercent'] = -1
            result['oldmax'] = oldmax
            result['newmax'] = oldmax
            result['reasonCode'] = result_score['reasonCode']
            result['boostAmount'] = boost_amount
            result['totalAmount'] = -1
            result['reasonCategory'] = None
            result['maxcap'] = result_score['maxcap'] if 'maxcap' in result_score else -1
            result['userId'] = user_id
        logger.info("Max adjustment result for user %d: %s", user_id, result, extra=d)
        return JSONResponse(content=result)

    except Exception as e:
        logger.exception("Max adjustment failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:max_adjustment"])
        raise ServiceUnavailable(f"Max adjustment request failed for user {user_id}")


@app.get("/express-future-max/{user_id}", operation_id="GetExpressFutureMax")
async def get_express_future_max(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Express future max requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:

        future_cap = fma.get_express_future_max(user_id)
        logger.info("Final output for user %d: %s", user_id, future_cap["futuremax"], extra=d)

        return JSONResponse(content=future_cap)

    except Exception as e:
        logger.exception("Express future max failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:express_future_max"])
        raise ServiceUnavailable(f"Express future max request failed for user {user_id}")


@app.get("/max-adjustment-act/{user_id}", operation_id="GetMaxAdjustmentAct")
async def get_max_adjustment_act(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Max adjustment act requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    result = dict()

    try:
        old_max = ma.get_old_max(user_id)
        result['score'] = -1
        result['tipPercent'] = -1
        result['oldmax'] = old_max
        result['newmax'] = old_max
        result['reasonCode'] = None
        result['boostAmount'] = ma.get_temp_max(user_id)
        result['totalAmount'] = -1
        result['reasonCategory'] = None
        result['maxcap'] = -1
        result['userId'] = user_id

        amt = ma.get_current_paycycle_usage(user_id)
        if old_max - amt >= 0:
            if result['boostAmount'] > 0:
                result['newmax'] = old_max
            else:
                result_score = ma.get_new_max(user_id, context_id)
                if 'newmax' in result_score:
                    result = result_score
                    result['maxcap'] = result_score['maxcap'] if 'maxcap' in result_score else -1
                    result['userId'] = user_id
                else:
                    result['reasonCode'] = result_score['reasonCode']
                if result['newmax'] < old_max:
                    result['newmax'] = old_max
        else:
            result['reasonCode'] = ['Still have available max']
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Max adjustment Act failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:max_adjustment_act"])
        raise ServiceUnavailable(f"Max adjustment act request failed for user {user_id}")

@app.get("/restore-grace-period/{user_id}", operation_id="GetRestoreGracePeriod")
async def get_restore_grace_period(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Restore grace period requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        result = rgp.get_grace_period(user_id, context_id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Restore grace period decision failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:restore_grace_period"])
        raise ServiceUnavailable(f"Restore grace period request failed for user {user_id}")


@app.get("/savings-deposit-request-risk/{user_id}", operation_id="GetSavingsDepositRequestRisk")
async def get_savings_deposit_request_risk(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("User savings deposit requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        # get experiment group
        experiment_id = 122
        user_exp = UserExperiment()
        group_id = user_exp.get_user_group(user_id, experiment_id)

        result = {"score": 0, "days": 0} if group_id == 1 else drr.get_days(user_id)
        result['userId'] = user_id
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("User savings deposit risk request failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:savings_deposit_request_risk"])
        raise ServiceUnavailable(f"Risk of user savings deposit request failed for user {user_id}")


@app.get("/request-max-adjustment", operation_id="GetRequestMaxAdjustment")
async def get_request_max_adjustment(request: Request, userid: int = None, desiredIncrease: int = None, desiredAdjustment: int = None):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": userid}
    logger.info("Max increase up to desired amount requested for user %d", userid, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", userid)

    if userid is None:
        userid = -1

    # put increase/adjustment together
    if desiredAdjustment is not None:
        desired_amt = desiredAdjustment
    elif desiredIncrease is not None:
        desired_amt = desiredIncrease
    else:
        desired_amt = None

    try:  # try getting and returning new max
        if userid > 0 and desired_amt is not None:  # valid userid, adjustment amount
            try:  # try calling increase function
                result = rma.try_adjustment(userid, desired_amt, context_id)
                logger.info("Final output for %d: %s", userid, str(result), extra=d)
                logger.info("Successfully processed max increase request for user %d", userid, extra=d)
                result['userid'] = userid
            except Exception as e:  # if call failed
                logger.exception("Unable to fully process max increase request for %d", userid, extra=d)
                oldmax = ma.get_old_max(userid)
                result = dict()
                result["userid"] = userid
                result["newmax"] = oldmax
                result["oldmax"] = oldmax
            return JSONResponse(content=result)
        else:  # log failure if arguments are invalid
            logger.exception("Invalid argument (userid or desiredIncrease) for %d", userid, extra=d)
            raise InvalidInput("Invalid argument (userid or desiredIncrease)")
    except Exception as e:  # log failure if didn't work
        logger.exception("Max increase up to desired amount request failed for user %d: %s", userid, str(e), extra=d)
        statsd.increment("exception", tags=["operation:request_max_adjustment"])
        raise ServiceUnavailable(f"Max adjustment request by desired amount for user {userid} failed")


@app.get("/new-user-max/{user_id}", operation_id="GetNewUserMax")
async def get_new_user_max(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Max increase up to desired amount requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        result = nu.get_max(user_id, context_id)
        result['userId'] = user_id
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("New user max request failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:new_user_max"])
        raise ServiceUnavailable(f"New user max request failed for user {user_id}")

@app.get("/failed-restore-user-max/{user_id}", operation_id="GetFailedRestoreUserMax")
async def get_failed_restore_user_max(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Restore failure max adjustment requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        result = rm.get_new_max(user_id, context_id)

        if 'newmax' in result:
            result['userId'] = user_id
        else:
            result = {}
            oldmax = rm.get_old_max(user_id)
            result['oldmax'] = oldmax
            result['newmax'] = oldmax
            result['userId'] = user_id
            result['reasonCode'] = 'not qualified for restore failure max adjustment'
            result['reasonCategory'] = None
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Restore failure max adjustment request failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:failed_restore_user_max"])
        raise ServiceUnavailable(f"Restore failure max adjustment request failed for user {user_id}")


@app.get("/success-recovery-max-adjustment/{user_id}", operation_id="GetSuccessRecoveryMaxAdjustment")
async def get_success_recovery_max_adjustment(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Recovery success max adjustment requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        prev_successful_restore, prev_failed_restore = rs.get_restore_count(user_id)
        days = rs.get_recovery_days(user_id)
        full_recovery = rs.full_recovery_check(user_id)
        last_max_adjustment = rs.found_max_adjustment(user_id)
        temp_max_boost = rs.temp_max_adjustment(user_id)
        decision = rs.get_max_decision(prev_successful_restore, prev_failed_restore, days, full_recovery,
                                       last_max_adjustment)
        old_max, current_max = rs.get_max_hist(user_id)
        result = rs.get_new_max(old_max, current_max, decision, temp_max_boost)

        result['userid'] = user_id
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Recovery success max adjustment request failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:success_recovery_max_adjustment"])
        raise ServiceUnavailable(f"Recovery success max adjustment request failed for user {user_id}")


@app.get("/payroll-grace-period/{user_id}", operation_id="GetPayrollGracePeriod")
async def get_payroll_grace_period(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Payroll grace period requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        result = pgp.get_grace_period(user_id, context_id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Payroll grace period request failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:payroll_grace_period"])
        raise ServiceUnavailable(f"Payroll grace period request failed for user {user_id}")


@app.get("/competitor-max-decision", operation_id="GetCompetitorMaxDecision")
async def get_competitor_max_decision(request: Request, userid: int = -1, max: int = -1):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": userid}
    logger.info("Competitor max decision requested for user %d", userid, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", userid)

    try:
        result = {'userId': userid}
        decision = mac.get_decision(userid, max, context_id)
        result.update(decision)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Competitor max decision request failed for user %d: %s", userid, str(e), extra=d)
        statsd.increment("exception", tags=["operation:competitor_max_decision"])
        raise ServiceUnavailable(f"Competitor max decision request failed for user {userid}")


@app.get("/unemployment-existing-user-check/{user_id}", operation_id="GetUnemploymentExistingUserCheck")
async def get_unemployment_existing_user_check(user_id: int, request: Request):
    context_id = request.headers.get('X-call-context-id')
    d = {"ContextId": context_id, "UserId": user_id}
    logger.info("Existing user unemployment check requested for user %d", user_id, extra=d)

    current_span = tracer.current_span()
    if current_span:
        current_span.set_tag("request.user_id", user_id)

    try:
        result = eu.existing_user_unemployment_check(user_id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Existing user unemployment check request failed for user %d: %s", user_id, str(e), extra=d)
        statsd.increment("exception", tags=["operation:unemployment_existing_user_check"])
        raise ServiceUnavailable(f"Existing user unemployment check request failed for user {user_id}")