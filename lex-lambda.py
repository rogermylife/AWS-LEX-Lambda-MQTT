"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages reservations for hotel rooms and car rentals.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'BookTrip' template.

For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""

import json
import datetime
import time
import os
import dateutil.parser
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# --- Helpers that build all of the responses ---


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


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
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


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# --- Helper Functions ---


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


def generate_car_price(location, days, age, car_type):
    """
    Generates a number within a reasonable range that might be expected for a flight.
    The price is fixed for a given pair of locations.
    """

    car_types = ['economy', 'standard', 'midsize', 'full size', 'minivan', 'luxury']
    base_location_cost = 0
    for i in range(len(location)):
        base_location_cost += ord(location.lower()[i]) - 97

    age_multiplier = 1.10 if age < 25 else 1
    # Select economy is car_type is not found
    if car_type not in car_types:
        car_type = car_types[0]

    return days * ((100 + base_location_cost) + ((car_types.index(car_type.lower()) * 50) * age_multiplier))


def generate_hotel_price(location, nights, room_type):
    """
    Generates a number within a reasonable range that might be expected for a hotel.
    The price is fixed for a pair of location and roomType.
    """

    room_types = ['queen', 'king', 'deluxe']
    cost_of_living = 0
    for i in range(len(location)):
        cost_of_living += ord(location.lower()[i]) - 97

    return nights * (100 + cost_of_living + (100 + room_types.index(room_type.lower())))


def isvalid_car_type(car_type):
    car_types = ['economy', 'standard', 'midsize', 'full size', 'minivan', 'luxury']
    return car_type.lower() in car_types


def isvalid_city(city):
    valid_cities = ['back','next']
    return city.lower() in valid_cities


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def get_day_difference(later_date, earlier_date):
    later_datetime = dateutil.parser.parse(later_date).date()
    earlier_datetime = dateutil.parser.parse(earlier_date).date()
    return abs(later_datetime - earlier_datetime).days


def add_days(date, number_of_days):
    new_date = dateutil.parser.parse(date).date()
    new_date += datetime.timedelta(days=number_of_days)
    return new_date.strftime('%Y-%m-%d')


def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


# def validate_book_car(slots):
#     pickup_city = try_ex(lambda: slots['PickUpCity'])
#     pickup_date = try_ex(lambda: slots['PickUpDate'])
#     return_date = try_ex(lambda: slots['ReturnDate'])
#     driver_age = safe_int(try_ex(lambda: slots['DriverAge']))
#     car_type = try_ex(lambda: slots['CarType'])

#     if pickup_city and not isvalid_city(pickup_city):
#         return build_validation_result(
#             False,
#             'PickUpCity',
#             'We currently do not support {} as a valid destination.  Can you try a different city?'.format(pickup_city)
#         )

#     if pickup_date:
#         if not isvalid_date(pickup_date):
#             return build_validation_result(False, 'PickUpDate', 'I did not understand your departure date.  When would you like to pick up your car rental?')
#         if datetime.datetime.strptime(pickup_date, '%Y-%m-%d').date() <= datetime.date.today():
#             return build_validation_result(False, 'PickUpDate', 'Reservations must be scheduled at least one day in advance.  Can you try a different date?')

#     if return_date:
#         if not isvalid_date(return_date):
#             return build_validation_result(False, 'ReturnDate', 'I did not understand your return date.  When would you like to return your car rental?')

#     if pickup_date and return_date:
#         if dateutil.parser.parse(pickup_date) >= dateutil.parser.parse(return_date):
#             return build_validation_result(False, 'ReturnDate', 'Your return date must be after your pick up date.  Can you try a different return date?')

#         if get_day_difference(pickup_date, return_date) > 30:
#             return build_validation_result(False, 'ReturnDate', 'You can reserve a car for up to thirty days.  Can you try a different return date?')

#     if driver_age is not None and driver_age < 18:
#         return build_validation_result(
#             False,
#             'DriverAge',
#             'Your driver must be at least eighteen to rent a car.  Can you provide the age of a different driver?'
#         )

#     if car_type and not isvalid_car_type(car_type):
#         return build_validation_result(
#             False,
#             'CarType',
#             'I did not recognize that model.  What type of car would you like to rent?  '
#             'Popular cars are economy, midsize, or luxury')

#     return {'isValid': True}


def validate_hotel(slots):
    action = try_ex(lambda: slots['Action'])
    # checkin_date = try_ex(lambda: slots['CheckInDate'])
    # nights = safe_int(try_ex(lambda: slots['Nights']))
    # room_type = try_ex(lambda: slots['RoomType'])

    if action and not isvalid_city(action):
        return build_validation_result(
            False,
            'Action',
            'We currently do not support {} as a valid action.  Can you try a different action?'.format(action)
        )

    # if checkin_date:
    #     if not isvalid_date(checkin_date):
    #         return build_validation_result(False, 'CheckInDate', 'I did not understand your check in date.  When would you like to check in?')
    #     if datetime.datetime.strptime(checkin_date, '%Y-%m-%d').date() <= datetime.date.today():
    #         return build_validation_result(False, 'CheckInDate', 'Reservations must be scheduled at least one day in advance.  Can you try a different date?')

    # if nights is not None and (nights < 1 or nights > 30):
    #     return build_validation_result(
    #         False,
    #         'Nights',
    #         'You can make a reservations for from one to thirty nights.  How many nights would you like to stay for?'
    #     )


    return {'isValid': True}


""" --- Functions that control the bot's behavior --- """


def book_hotel(intent_request):
    """
    Performs dialog management and fulfillment for booking a hotel.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """

    location = try_ex(lambda: intent_request['currentIntent']['slots']['Action'])
    # checkin_date = try_ex(lambda: intent_request['currentIntent']['slots']['CheckInDate'])
    # nights = safe_int(try_ex(lambda: intent_request['currentIntent']['slots']['Nights']))

    # room_type = try_ex(lambda: intent_request['currentIntent']['slots']['RoomType'])
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # Load confirmation history and track the current reservation.
    reservation = json.dumps({
        'ReservationType': 'Hotel',
        'Location': location,
        # 'RoomType': room_type,
        # 'CheckInDate': checkin_date,
        # 'Nights': nights
    })

    session_attributes['currentReservation'] = reservation

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_hotel(intent_request['currentIntent']['slots'])
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

        # Otherwise, let native DM rules determine how to elicit for slots and prompt for confirmation.  Pass price
        # back in sessionAttributes once it can be calculated; otherwise clear any setting from sessionAttributes.
        if location :
            # The price of the hotel has yet to be confirmed.
            # price = generate_hotel_price(location, nights, room_type)
            session_attributes['currentReservationPrice'] = 100
        else:
            try_ex(lambda: session_attributes.pop('currentReservationPrice'))

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    # Booking the hotel.  In a real application, this would likely involve a call to a backend service.
    logger.debug('bookHotel under={}'.format(reservation))

    try_ex(lambda: session_attributes.pop('currentReservationPrice'))
    try_ex(lambda: session_attributes.pop('currentReservation'))
    session_attributes['lastConfirmedReservation'] = reservation

    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Done'
        }
    )


# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'BookHotel':
        return book_hotel(intent_request)
    if intent_name == 'Remote':
        return book_hotel(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'Asia/Taipei'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
