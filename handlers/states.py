from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_phone = State()

class QuizStates(StatesGroup):
    answering = State()

class ManagerActionStates(StatesGroup):
    waiting_for_trial_date = State()
    waiting_for_note = State()

class AdminBroadcastStates(StatesGroup):
    waiting_for_target = State()
    waiting_for_user_id = State()
    waiting_for_message = State()

class AdminEventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_desc = State()
    waiting_for_datetime = State()
    waiting_for_seats = State()

class AdminManagementStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_admin_name = State()

class PromocodeStates(StatesGroup):
    waiting_for_code = State()
