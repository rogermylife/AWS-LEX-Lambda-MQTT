import json
import datetime
import time
import os
import dateutil.parser
import logging
import boto3
import urllib2

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
client = boto3.client('iot-data', region_name='us-east-1')
# ---Helper functions
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def try_ex(func):
    try:
        return func()
    except KeyError:
        return None

def isvalid_action(action):
    valid_actions = ['back','next','louder','smaller','power']
    return action.lower() in valid_actions

def build_validation_result(isvalid,violated_slot,message_content):
    return {
        'isValid':isvalid,
        'violatedSlot':violated_slot,
        'message':{'contentType':'PlainText','content':message_content}
    }

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response

def validate_remote(slots):
    action = try_ex(lambda: slots['Action'])
    if action and not isvalid_action(action):
        return build_validation_result(
            False,
            'Action',
            'We currently do not support {} as a valid action.  Can you try a different action?'.format(action)
        )
    return {'isValid': True}

def remote(intent_request):
    action = try_ex(lambda: intent_request['currentIntent']['slots']['Action'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    reservation = json.dumps({
        'ReservationType': 'Type',
        'Action': action
    })
    session_attributes['currentReservation'] = reservation
    if intent_request['invocationSource'] == 'DialogCodeHook':
        validation_result = validate_remote(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots = intent_request['currentIntent']['slots']
            slots[validation_result['violatedSlot']] = None

            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])
    
    #  In a real application, this would likely involve a call to a backend service.
    logger.debug('Remote under={}'.format(reservation))

    try_ex(lambda: session_attributes.pop('currentReservation'))
    session_attributes['lastConfirmedReservation'] = reservation

    response = client.publish(
            topic='PiInput',
            qos=1,
            payload=json.dumps({
                "Method":"Remote",
                "Action" : action
                
            })
        )
    
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Done Action '+action
        }
    )


def validate_turn(slots):
    channel_number = try_ex(lambda: slots['ChannelNumber'])
    if channel_number and not channel_number.isnumeric():
        return build_validation_result(
            False,
            'ChannelNumber',
            'We currently do not support {} as a valid channel number.  Can you try a different number?'.format(channel_number)
        )
    return {'isValid': True}

def turn(intent_request):
    channel_number = try_ex(lambda: intent_request['currentIntent']['slots']['ChannelNumber'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    reservation = json.dumps({
        'ReservationType': 'Type',
        'ChannelNumber': channel_number
    })
    session_attributes['currentReservation'] = reservation
    if intent_request['invocationSource'] == 'DialogCodeHook':
        validation_result = validate_turn(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots = intent_request['currentIntent']['slots']
            slots[validation_result['violatedSlot']] = None

            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])
    
    #  In a real application, this would likely involve a call to a backend service.
    logger.debug('Remote under={}'.format(reservation))

    try_ex(lambda: session_attributes.pop('currentReservation'))
    session_attributes['lastConfirmedReservation'] = reservation
    

    # Change topic, qos and payload
    response = client.publish(
            topic='PiInput',
            qos=1,
            payload=json.dumps({
                "Method":"Turn",
                "ChannelNumber" : channel_number
            })
        )
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Done channel '+channel_number
        }
    )

def watch(intent_request):
    show = try_ex(lambda: intent_request['currentIntent']['slots']['Show'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    reservation = json.dumps({
        'ReservationType': 'Type',
        'Show': show
    })
    session_attributes['currentReservation'] = reservation
    if intent_request['invocationSource'] == 'DialogCodeHook':

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])
    
    #  In a real application, this would likely involve a call to a backend service.
    logger.debug('Watch under={}'.format(reservation))

    try_ex(lambda: session_attributes.pop('currentReservation'))
    session_attributes['lastConfirmedReservation'] = reservation
    print "SHOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOW" + show
    data = {
        'q': show
    }

    req = urllib2.Request('https://fpe50kpobl.execute-api.us-east-1.amazonaws.com/zzzz')
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, json.dumps(data))
    data = json.loads(response.read())
    channel_number =''
    try:
        channel_number = data['body-json']['errorMessage']
        print "MMMMMMMMMMMMMMMMMMMMMMMMMMMM  ",channel_number
        if channel_number.isnumeric():
            # Change topic, qos and payload
            response = client.publish(
                    topic='PiInput',
                    qos=1,
                    payload=json.dumps({
                        "Method":"Turn",
                        "ChannelNumber" : channel_number
                    })
                )
            responseContent = 'Done channel for '+show+' '+channel_number
        else :
            responseContent = 'Sorry! There is no '+show+' for you.'+channel_number
    except:
        channel_number = 'null'
        responseContent ='error'
    
    print 'WHAT'
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': responseContent
        }
    )




def dispatch(intent_request):
    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))
    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'Remote':
        return remote(intent_request)
    elif intent_name == 'Turn':
        return turn(intent_request)
    elif intent_name == 'Watch':
        return watch(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    os.environ['TZ'] = 'Asia/Taipei'
    time.tzset()
    logger.debug('event.bot.name{}'.format(event['bot']['name']))
    return dispatch(event)